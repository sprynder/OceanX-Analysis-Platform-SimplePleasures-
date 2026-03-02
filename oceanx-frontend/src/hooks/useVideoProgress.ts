import { useEffect, useState, useCallback } from 'react';

export interface ProgressEvent {
  type: 'processing_started' | 'frame_progress' | 'processing_complete' | 'error';
  video_id: string;
  frame_index?: number;
  frames_processed?: number;
  total_frames?: number;
  rois_detected?: number;
  message?: string;
  status?: string;
}

export function useVideoProgress(videoId: string | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<ProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!videoId) {
      console.log('[WS] No videoId, skipping connection');
      return;
    }

    // // Construct WebSocket URL from API_BASE (same as other API calls)
    // const apiBase = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, '') || 'http://localhost:8080';
    
    // // Parse the URL to get protocol and host
    // const url = new URL(apiBase);
    // const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    // const host = url.host; // localhost:8080
    // const wsUrl = `${protocol}//${host}/ws/videos/${videoId}`;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/videos/${videoId}`;

    console.log('[WS] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[WS] Connected for video:', videoId);
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data: ProgressEvent = JSON.parse(event.data);
        console.log('[WS] Progress event:', data);
        setLastEvent(data);
        setEvents((prev) => [...prev, data]);
      } catch (e) {
        console.error('[WS] Failed to parse message:', e);
      }
    };

    ws.onerror = (event) => {
      console.error('[WS] Error:', event);
      setError('WebSocket connection error');
    };

    ws.onclose = (event) => {
      console.log('[WS] Disconnected (code:', event.code, 'reason:', event.reason, ')');
      setIsConnected(false);
    };

    return () => {
      console.log('[WS] Cleanup - closing connection');
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [videoId]);

  return {
    isConnected,
    events,
    lastEvent,
    error,
    progress: lastEvent?.frames_processed ?? 0,
    totalRois: lastEvent?.rois_detected ?? 0,
  };
}
