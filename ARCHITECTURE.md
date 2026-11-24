# Real-Time Collaboration Architecture

## Overview
CollabFlow uses WebSockets to enable real-time synchronization of task updates across multiple connected clients viewing the same project.

## Architecture Diagram

```
┌─────────────────────┐                    ┌─────────────────────┐
│   Browser Window 1  │                    │   Browser Window 2  │
│                     │                    │                     │
│  ┌───────────────┐  │                    │  ┌───────────────┐  │
│  │  React Board  │  │                    │  │  React Board  │  │
│  │    Component  │  │                    │  │    Component  │  │
│  └───────┬───────┘  │                    │  └───────┬───────┘  │
│          │          │                    │          │          │
│          │ User     │                    │          │          │
│          │ drags    │                    │          │ Updates  │
│          │ task     │                    │          │ auto-    │
│          ↓          │                    │          │ matically│
│  ┌───────────────┐  │                    │          ↓          │
│  │  WebSocket    │  │                    │  ┌───────────────┐  │
│  │   Service     │◄─┼────────────────────┼─►│  WebSocket    │  │
│  └───────┬───────┘  │                    │  │   Service     │  │
└──────────┼──────────┘                    └──┼───────────────┘  │
           │                                   │                  │
           │ HTTP POST/PATCH                   │ WS Message       │
           │ /api/v1/tasks                     │ received         │
           ↓                                   ↑                  │
    ═══════════════════════════════════════════════════════════  │
           │          FastAPI Backend          │                  │
    ═══════════════════════════════════════════════════════════  │
           ↓                                   ↑                  │
  ┌────────────────────────────────────────────────────┐         │
  │             Task API Endpoints                      │         │
  │          (app/api/tasks.py)                        │         │
  │                                                     │         │
  │  POST   /tasks      - Create task                  │         │
  │  PATCH  /tasks/{id} - Update task (drag & drop)    │         │
  │  DELETE /tasks/{id} - Delete task                  │         │
  │  POST   /tasks/dependencies - Add dependency       │         │
  │  DELETE /tasks/dependencies/{id} - Remove dep      │         │
  │                                                     │         │
  │  After each mutation:                              │         │
  │  ┌──────────────────────────────────────────┐     │         │
  │  │ await manager.broadcast_to_project(      │     │         │
  │  │     project_id,                          │     │         │
  │  │     {                                    │     │         │
  │  │         "type": "task_updated",          │     │         │
  │  │         "task_id": task.id,              │     │         │
  │  │         "task": {...}                    │     │         │
  │  │     }                                    │     │         │
  │  │ )                                        │     │         │
  │  └──────────────────┬───────────────────────┘     │         │
  └─────────────────────┼─────────────────────────────┘         │
                        ↓                                        │
  ┌──────────────────────────────────────────────────┐          │
  │        Connection Manager                        │          │
  │     (app/realtime/connection_manager.py)         │          │
  │                                                   │          │
  │  Maintains:                                      │          │
  │  - active_connections: {project_id → Set[WS]}   │          │
  │  - connection_users: {WebSocket → user_id}      │          │
  │  - connection_projects: {WebSocket → project_id}│          │
  │                                                   │          │
  │  broadcast_to_project():                        │          │
  │    For all WebSockets in project:              │          │
  │      websocket.send_json(message) ──────────────┼──────────┘
  │                                                  │
  └──────────────────────────────────────────────────┘
```

## Component Details

### Frontend: BoardPage.tsx
```typescript
// Connects to WebSocket on mount
useEffect(() => {
  const token = getTokenFromCookie()
  wsService.connect(projectId, token)
  
  // Listen for messages
  const unsubscribe = wsService.onMessage((message) => {
    if (['task_created', 'task_updated', 'task_deleted'].includes(message.type)) {
      queryClient.invalidateQueries({ queryKey: ['tasks', projectId] })
    }
  })
  
  return () => {
    unsubscribe()
    wsService.disconnect()
  }
}, [projectId])
```

**When user drags task:**
1. Optimistically update local state
2. Send PATCH request to backend
3. Backend saves to database
4. Backend broadcasts WebSocket message
5. All connected clients receive message
6. Each client invalidates cache and refetches
7. UI updates with fresh data

### Backend: WebSocket Endpoint
```python
# app/realtime/websocket.py
@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...)
):
    # Authenticate user
    user = verify_token(token)
    
    # Verify project access
    verify_project_access(project_id, user)
    
    # Connect to manager
    await manager.connect(websocket, project_id, user.id)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Handle incoming messages (ping/pong, etc.)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### Backend: Task API (The Fix)
```python
# app/api/tasks.py
@router.patch("/{task_id}")
async def update_task(task_id: str, task_data: TaskUpdate, ...):
    # 1. Load task from database
    task = db.query(Task).filter(Task.id == task_id).first()
    
    # 2. Verify permissions and version
    verify_project_access(task.project_id, current_user, db)
    if task.version != task_data.version:
        raise HTTPException(409, "Conflict")
    
    # 3. Update task fields
    task.status = task_data.status
    task.version += 1
    
    # 4. Save to database
    db.commit()
    db.refresh(task)
    
    # 5. ✨ NEW: Broadcast to all connected clients ✨
    await manager.broadcast_to_project(
        task.project_id,
        {
            "type": "task_updated",
            "task_id": task.id,
            "task": {
                "id": task.id,
                "status": task.status,
                "version": task.version,
                ...
            }
        }
    )
    
    return task
```

## Message Types

### task_created
Sent when a new task is created.
```json
{
  "type": "task_created",
  "task_id": "uuid",
  "task": {
    "id": "uuid",
    "title": "New Task",
    "status": "TODO",
    "priority": "MEDIUM",
    "position": 0,
    "version": 1
  }
}
```

### task_updated
Sent when a task is modified (including drag-and-drop).
```json
{
  "type": "task_updated",
  "task_id": "uuid",
  "task": {
    "id": "uuid",
    "title": "Updated Task",
    "status": "IN_PROGRESS",
    "priority": "HIGH",
    "position": 2,
    "version": 5,
    "assignee_id": "uuid"
  }
}
```

### task_deleted
Sent when a task is deleted.
```json
{
  "type": "task_deleted",
  "task_id": "uuid"
}
```

### dependency_added
Sent when a task dependency is created.
```json
{
  "type": "dependency_added",
  "dependency_id": "uuid",
  "task_id": "uuid",
  "depends_on_id": "uuid"
}
```

### dependency_removed
Sent when a task dependency is deleted.
```json
{
  "type": "dependency_removed",
  "dependency_id": "uuid",
  "task_id": "uuid",
  "depends_on_id": "uuid"
}
```

## Data Flow: Drag and Drop Example

```
User drags task from TODO to IN_PROGRESS in Browser 1:

1. Browser 1: User drags task
   ↓
2. Browser 1: Optimistic update (UI shows task in IN_PROGRESS immediately)
   ↓
3. Browser 1: PATCH /api/v1/tasks/{id} { status: "IN_PROGRESS", version: 3 }
   ↓
4. Backend: Validate user has permission
   ↓
5. Backend: Check version matches (optimistic concurrency control)
   ↓
6. Backend: Update task.status = "IN_PROGRESS", task.version = 4
   ↓
7. Backend: db.commit()
   ↓
8. Backend: manager.broadcast_to_project(project_id, {type: "task_updated", ...})
   ↓
9. Backend: Send message to all WebSocket connections for this project
   ↓
10. Browser 1: Receives WebSocket message → invalidates cache → refetches → confirms UI
    ↓
11. Browser 2: Receives WebSocket message → invalidates cache → refetches → updates UI
    ↓
12. All browsers now show task in IN_PROGRESS column
```

## Key Features

### Optimistic Concurrency Control
- Each task has a `version` field that increments on every update
- Client must send current version with update request
- If versions don't match, server returns 409 Conflict
- Prevents lost updates when multiple users edit simultaneously

### Automatic Reconnection
- Frontend WebSocket service has built-in reconnection logic
- Exponential backoff: 1s, 2s, 4s, 8s, 16s
- Maximum 5 reconnection attempts
- Heartbeat ping every 30 seconds to detect stale connections

### Room-Based Broadcasting
- Connections organized by project_id
- Broadcasts only sent to users viewing the same project
- Efficient - doesn't send unnecessary messages
- Each user can be in multiple project "rooms" simultaneously

### Authentication
- WebSocket connections require valid JWT token
- Token passed as query parameter: `ws://host/ws/{project_id}?token={jwt}`
- Backend verifies token and project access before accepting connection
- Invalid tokens or unauthorized users are rejected

## Performance Considerations

### Scalability
Current implementation uses in-memory connection storage:
- ✅ Fine for single-server deployments
- ⚠️  For multi-server: Need Redis pub/sub or message broker
- ⚠️  For 1000+ concurrent users: Consider WebSocket server clustering

### Message Size
- Keep broadcast messages small (only essential data)
- Current messages: ~200-500 bytes each
- Frontend refetches full data from HTTP API after receiving notification
- Alternative: Send complete task object in message (avoid refetch but larger messages)

### Database Load
- Each WebSocket message triggers cache invalidation
- Cache invalidation triggers HTTP API call
- API call queries database
- For high-traffic projects: Consider debouncing or batch updates

## Security

### Authentication
- ✅ WebSocket connections require valid JWT
- ✅ Project access verified before accepting connection
- ✅ Token validation on every connection attempt

### Authorization
- ✅ User must have read access to project to connect
- ✅ Workspace membership checked
- ✅ No sensitive data in broadcast messages (only task IDs and basic fields)

### Input Validation
- ✅ All task mutations validate through Pydantic schemas
- ✅ SQL injection prevented by SQLAlchemy ORM
- ✅ XSS prevented by React (automatic escaping)

## Monitoring

### Backend Logs
```python
logger.info(f"User {user_id} connected to project {project_id}")
logger.info(f"User {user_id} disconnected from project {project_id}")
logger.error(f"Error broadcasting to connection: {e}")
```

### Browser Console
```javascript
console.log(`WebSocket connected to project ${projectId}`)
console.log('WebSocket disconnected')
console.log('Reconnecting in Xms (attempt Y/5)')
```

### Metrics to Track
- Active WebSocket connections per project
- Message broadcast latency
- Reconnection rate
- Connection failures
- Messages sent/received per second

## Future Enhancements

### Presence Indicators
Show who else is viewing the project:
```json
{
  "type": "user_joined",
  "user_id": "uuid",
  "user_name": "Alice",
  "project_id": "uuid"
}
```

### Collaborative Cursors
Show where other users are clicking/dragging:
```json
{
  "type": "cursor_move",
  "user_id": "uuid",
  "x": 100,
  "y": 200
}
```

### Conflict Resolution UI
When version conflicts occur, show diff and let user choose:
```
Task was modified by another user:
- Their version: "Complete user authentication"
- Your version: "Complete authentication feature"
[Keep Theirs] [Keep Mine] [Merge]
```

### Operational Transforms
For true real-time collaborative editing of task titles/descriptions:
- Apply changes character-by-character
- Resolve conflicts automatically
- Similar to Google Docs
