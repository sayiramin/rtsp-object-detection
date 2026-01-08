import React, { useState, useEffect } from 'react';
import VideoStream from './components/VideoStream';
import Alerts from './components/Alerts';
import ZoneConfig from './components/ZoneConfig';
import './App.css';

interface Zone {
  id: string;
  points: [number, number][];
}

function App() {
  const [zones, setZones] = useState<string[]>([]);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [newZoneId, setNewZoneId] = useState('');

  const API_BASE = 'http://localhost:8002';
  const WS_VIDEO = 'ws://localhost:8002/ws/video';
  const WS_ALERTS = 'ws://localhost:8002/ws/alerts';

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/status`);
      const status = await response.json();
      setSystemStatus(status);
      setZones(status.zones || []);
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    }
  };

  const handleZoneDrawn = async (points: [number, number][]) => {
    if (!newZoneId.trim()) {
      alert('Please enter a zone ID first');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/zones`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: newZoneId,
          points: points
        }),
      });

      if (response.ok) {
        setZones(prev => [...prev, newZoneId]);
        setNewZoneId('');
        setIsDrawingMode(false);
        console.log('Zone added successfully');
      } else {
        console.error('Failed to add zone');
      }
    } catch (error) {
      console.error('Error adding zone:', error);
    }
  };

  const handleRemoveZone = async (zoneId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/zones/${zoneId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setZones(prev => prev.filter(id => id !== zoneId));
        console.log('Zone removed successfully');
      } else {
        console.error('Failed to remove zone');
      }
    } catch (error) {
      console.error('Error removing zone:', error);
    }
  };

  const startDrawing = () => {
    if (!newZoneId.trim()) {
      alert('Please enter a zone ID first');
      return;
    }
    setIsDrawingMode(true);
  };

  const cancelDrawing = () => {
    setIsDrawingMode(false);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>🎥 RTSP Object Detection System</h1>
        <div className="system-status">
          <span className={`status ${systemStatus?.pipeline_running ? 'running' : 'stopped'}`}>
            {systemStatus?.pipeline_running ? '🟢 System Running' : '🔴 System Stopped'}
          </span>
        </div>
      </header>

      <main className="app-main">
        <div className="video-section">
          <VideoStream 
            wsUrl={WS_VIDEO} 
            onZoneDrawn={handleZoneDrawn}
            isDrawingMode={isDrawingMode}
          />
        </div>

        <div className="control-panel">
          <div className="alerts-section">
            <Alerts wsUrl={WS_ALERTS} />
          </div>

          <div className="config-section">
            <h3>Zone Configuration</h3>
            
            <div className="zone-input">
              <input
                type="text"
                placeholder="Zone ID (e.g., restricted-area-1)"
                value={newZoneId}
                onChange={(e) => setNewZoneId(e.target.value)}
                disabled={isDrawingMode}
              />
              <div className="zone-buttons">
                {!isDrawingMode ? (
                  <button onClick={startDrawing} className="btn-draw">
                    🎯 Draw Zone
                  </button>
                ) : (
                  <button onClick={cancelDrawing} className="btn-cancel">
                    ❌ Cancel Drawing
                  </button>
                )}
              </div>
            </div>

            <div className="existing-zones">
              <h4>Active Zones ({zones.length})</h4>
              {zones.length === 0 ? (
                <p>No zones configured</p>
              ) : (
                zones.map(zoneId => (
                  <div key={zoneId} className="zone-item">
                    <span>🚫 {zoneId}</span>
                    <button 
                      onClick={() => handleRemoveZone(zoneId)}
                      className="btn-remove"
                    >
                      Delete
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
