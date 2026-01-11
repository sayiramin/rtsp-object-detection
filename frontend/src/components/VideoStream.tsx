import React, { useEffect, useRef, useState } from 'react';

interface VideoStreamProps {
  wsUrl: string;
  onZoneDrawn: (points: [number, number][]) => void;
  isDrawingMode: boolean;
}

const VideoStream: React.FC<VideoStreamProps> = ({ wsUrl, onZoneDrawn, isDrawingMode }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [connected, setConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [drawingPoints, setDrawingPoints] = useState<[number, number][]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setReconnectAttempts(0);
        console.log('Video WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'frame' && data.data) {
            drawFrame(data.data);
          }
          if (data.type === 'error') {
            console.error('Backend error:', data.message);
          }
        } catch (error) {
          console.error('Error parsing video data:', error);
        }
      };

      ws.onclose = (event) => {
        setConnected(false);
        console.log('Video WebSocket disconnected:', event.code, event.reason);
        
        if (reconnectAttempts < 10) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connectWebSocket();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('Video WebSocket error:', error);
        setConnected(false);
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnected(false);
    }
  };

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [wsUrl]);

  const drawFrame = (base64Data: string) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
      
      // Draw current drawing points with enhanced visuals
      if (isDrawingMode && drawingPoints.length > 0) {
        // Draw connecting lines
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]); // Dashed line
        ctx.beginPath();
        ctx.moveTo(drawingPoints[0][0], drawingPoints[0][1]);
        for (let i = 1; i < drawingPoints.length; i++) {
          ctx.lineTo(drawingPoints[i][0], drawingPoints[i][1]);
        }
        ctx.stroke();
        ctx.setLineDash([]); // Reset to solid line
        
        // Draw points with numbers
        drawingPoints.forEach((point, index) => {
          // Draw point circle
          ctx.fillStyle = '#00ff00';
          ctx.beginPath();
          ctx.arc(point[0], point[1], 6, 0, 2 * Math.PI);
          ctx.fill();
          
          // Draw point border
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(point[0], point[1], 6, 0, 2 * Math.PI);
          ctx.stroke();
          
          // Draw point number
          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText((index + 1).toString(), point[0], point[1]);
        });
        
        // Draw preview line to show where next point would connect
        if (drawingPoints.length >= 3) {
          ctx.strokeStyle = '#ffff00';
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          ctx.beginPath();
          ctx.moveTo(drawingPoints[drawingPoints.length - 1][0], drawingPoints[drawingPoints.length - 1][1]);
          ctx.lineTo(drawingPoints[0][0], drawingPoints[0][1]);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }
    };
    img.onerror = (error) => {
      console.error('Error loading frame image:', error);
    };
    img.src = `data:image/jpeg;base64,${base64Data}`;
  };

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawingMode) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    
    // Get the actual canvas dimensions vs display dimensions
    const displayWidth = rect.width;
    const displayHeight = rect.height;
    const actualWidth = canvas.width;
    const actualHeight = canvas.height;
    
    // Calculate click position relative to actual canvas size
    const clickX = (event.clientX - rect.left) * (actualWidth / displayWidth);
    const clickY = (event.clientY - rect.top) * (actualHeight / displayHeight);
    
    const newPoints: [number, number][] = [...drawingPoints, [Math.round(clickX), Math.round(clickY)]];
    setDrawingPoints(newPoints);
    
    console.log(`Added point: (${Math.round(clickX)}, ${Math.round(clickY)}) - Canvas: ${actualWidth}x${actualHeight}, Display: ${displayWidth}x${displayHeight}`);
    
    // If we have at least 3 points and user double-clicks, finish the zone
    if (newPoints.length >= 3 && event.detail === 2) {
      console.log('Finishing zone with points:', newPoints);
      onZoneDrawn(newPoints);
      setDrawingPoints([]);
    }
  };

  const clearDrawing = () => {
    setDrawingPoints([]);
  };

  return (
    <div className="video-stream">
      <div className="stream-header">
        <h3>Live Detection Feed</h3>
        <div className="connection-status">
          <span className={`status ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
          {!connected && reconnectAttempts > 0 && (
            <span className="reconnect-info">
              Reconnecting... ({reconnectAttempts}/10)
            </span>
          )}
        </div>
      </div>
      
      {isDrawingMode && (
        <div className="drawing-instructions">
          <p>🎯 Zone Drawing Mode: Click to add points ({drawingPoints.length} points)</p>
          {drawingPoints.length >= 3 && (
            <p>✅ Ready to finish! Double-click or press 'Complete Zone' to finish</p>
          )}
          {drawingPoints.length > 0 && (
            <button onClick={clearDrawing} className="clear-btn">Clear Points</button>
          )}
          {drawingPoints.length >= 3 && (
            <button onClick={() => {
              onZoneDrawn(drawingPoints);
              setDrawingPoints([]);
            }} className="complete-btn">Complete Zone</button>
          )}
        </div>
      )}
          <p>Points: {drawingPoints.length}</p>
          <button onClick={clearDrawing} className="btn-clear">Clear Points</button>
        </div>
      )}
      
      <div className="video-container">
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          style={{
            maxWidth: '100%',
            height: 'auto',
            border: '2px solid #333',
            borderRadius: '8px',
            backgroundColor: '#000',
            cursor: isDrawingMode ? 'crosshair' : 'default'
          }}
        />
        {!connected && (
          <div className="video-overlay">
            <div className="overlay-message">
              {reconnectAttempts === 0 ? 'Connecting to video stream...' : 
               reconnectAttempts < 10 ? 'Reconnecting...' : 'Connection failed'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoStream;
