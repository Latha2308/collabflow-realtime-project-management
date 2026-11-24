/**
 * WebSocket service for real-time collaboration.
 * Handles connection management, reconnection, and message routing.
 */

import type { WSMessage } from '@/types';

const WS_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8001';

type MessageHandler = (message: WSMessage) => void;
type ConnectionHandler = () => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private projectId: string | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private disconnectionHandlers: Set<ConnectionHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private isIntentionallyClosed = false;

  connect(projectId: string) {
    if (this.ws?.readyState === WebSocket.OPEN && this.projectId === projectId) {
      return; // Already connected to this project
    }

    this.disconnect(); // Close existing connection

    this.projectId = projectId;
    this.isIntentionallyClosed = false;

    // Browser automatically includes HttpOnly cookies in WebSocket handshake
    const url = `${WS_URL}/ws/${projectId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.connectionHandlers.forEach(handler => handler());
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.messageHandlers.forEach(handler => handler(message));
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      this.disconnectionHandlers.forEach(handler => handler());

      if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect();
      }
    };
  }

  disconnect() {
    this.isIntentionallyClosed = true;
    this.stopHeartbeat();
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.projectId = null;
    this.reconnectAttempts = 0;
  }

  send(message: Omit<WSMessage, 'user_id' | 'timestamp'>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const fullMessage: WSMessage = {
        ...message,
        timestamp: new Date().toISOString(),
      };
      this.ws.send(JSON.stringify(fullMessage));
    } else {
      console.warn('WebSocket is not connected, cannot send message');
    }
  }

  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnection(handler: ConnectionHandler) {
    this.connectionHandlers.add(handler);
    return () => this.connectionHandlers.delete(handler);
  }

  onDisconnection(handler: ConnectionHandler) {
    this.disconnectionHandlers.add(handler);
    return () => this.disconnectionHandlers.delete(handler);
  }

  private scheduleReconnect() {
    this.reconnectAttempts++;
    
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 16000);
    
    this.reconnectTimeout = setTimeout(() => {
      if (this.projectId) {
        this.connect(this.projectId);
      }
    }, delay);
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 30000); // Send heartbeat every 30 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getProjectId(): string | null {
    return this.projectId;
  }
}

// Singleton instance
export const wsService = new WebSocketService();
