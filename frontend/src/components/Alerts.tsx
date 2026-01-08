import React, { useEffect, useState } from 'react';

interface Alert {
  type: string;
  timestamp: number;
  bbox?: number[];
  zone_id?: string;
  confidence?: number;
  message?: string;
}

interface AlertsProps {
  wsUrl: string;
}

const Alerts: React.FC<AlertsProps> = ({ wsUrl }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connected, setConnected] = useState(false);
  const [connectionAttempts, setConnectionAttempts] = useState(0);

  const connectWebSocket = () => {
    console.log(`Attempting to connect to: ${wsUrl}`);
    
    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setConnected(true);
        setConnectionAttempts(0);
        console.log('✅ Alerts WebSocket connected successfully');
        
        // Add a test alert to confirm connection
        setAlerts(prev => [...prev, {
          type: 'connection_test',
          timestamp: Date.now() / 1000,
          message: '✅ WebSocket connection established'
        }]);
      };

      ws.onmessage = (event) => {
        console.log('📨 Received WebSocket message:', event.data);
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'alerts' && data.data) {
            console.log('📢 Adding alerts:', data.data);
            setAlerts(prev => [...prev, ...data.data].slice(-20));
          }
          
          if (data.type === 'connection_status' && data.status === 'connected') {
            console.log('✅ Connection confirmed:', data.message);
            setAlerts(prev => [...prev, {
              type: 'connection_confirmed',
              timestamp: Date.now() / 1000,
              message: '🔗 Backend connection confirmed'
            }]);
          }
        } catch (error) {
          console.error('❌ Error parsing WebSocket data:', error);
        }
      };

      ws.onclose = (event) => {
        setConnected(false);
        console.log(`❌ WebSocket closed: ${event.code} - ${event.reason}`);
        
        // Retry connection
        if (connectionAttempts < 10) {
          setTimeout(() => {
            setConnectionAttempts(prev => prev + 1);
            connectWebSocket();
          }, 2000);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setConnected(false);
      };

    } catch (error) {
      console.error('❌ Failed to create WebSocket:', error);
      setConnected(false);
    }
  };

  useEffect(() => {
    connectWebSocket();
  }, [wsUrl]);

  const formatTime = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'no_headgear': return '⚠️';
      case 'zone_violation': return '🚫';
      case 'chair_moved_with_person': return '🪑';
      case 'chair_moved_alone': return '🚨';
      case 'person_walking': return '🚶';
      case 'connection_test': return '🔗';
      case 'connection_confirmed': return '✅';
      case 'system_ready': return '🚀';
      default: return '🔔';
    }
  };

  const getAlertMessage = (alert: Alert) => {
    if (alert.message) {
      return alert.message;
    }
    
    switch (alert.type) {
      case 'chair_moved_with_person':
        return 'Person moving chair detected';
      case 'chair_moved_alone':
        return 'SUSPICIOUS: Chair moving without visible person';
      default:
        return `Alert: ${alert.type}`;
    }
  };

  return (
    <div className="alerts-panel">
      <div className="alerts-header">
        <h3>Live Alerts</h3>
        <div className="connection-info">
          <span className={`status ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
          {!connected && connectionAttempts > 0 && (
            <div className="reconnect-info">
              Reconnecting... ({connectionAttempts}/10)
            </div>
          )}
        </div>
      </div>
      <div className="alerts-list">
        {alerts.length === 0 ? (
          <div className="no-alerts">
            <p>Waiting for real movement alerts...</p>
            <p>Move a chair to see alerts!</p>
            <button onClick={connectWebSocket} className="btn-reconnect">
              🔄 Reconnect
            </button>
          </div>
        ) : (
          alerts.map((alert, index) => (
            <div key={`${alert.timestamp}-${index}`} className={`alert-item ${alert.type}`}>
              <div className="alert-icon">{getAlertIcon(alert.type)}</div>
              <div className="alert-content">
                <div className="alert-message">{getAlertMessage(alert)}</div>
                <div className="alert-time">{formatTime(alert.timestamp)}</div>
                {alert.confidence && (
                  <div className="alert-confidence">
                    Confidence: {(alert.confidence * 100).toFixed(1)}%
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Alerts;
