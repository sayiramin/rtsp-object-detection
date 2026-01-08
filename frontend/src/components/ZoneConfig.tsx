import React, { useState } from 'react';

interface Zone {
  id: string;
  points: [number, number][];
}

interface ZoneConfigProps {
  onAddZone: (zone: Zone) => void;
  onRemoveZone: (zoneId: string) => void;
  zones: string[];
}

const ZoneConfig: React.FC<ZoneConfigProps> = ({ onAddZone, onRemoveZone, zones }) => {
  const [newZoneId, setNewZoneId] = useState('');
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentPoints, setCurrentPoints] = useState<[number, number][]>([]);

  const handleAddZone = () => {
    if (!newZoneId.trim()) {
      alert('Please enter a zone ID');
      return;
    }

    if (currentPoints.length < 3) {
      alert('Please draw at least 3 points for the zone');
      return;
    }

    onAddZone({
      id: newZoneId,
      points: currentPoints
    });

    setNewZoneId('');
    setCurrentPoints([]);
    setIsDrawing(false);
  };

  const startDrawing = () => {
    if (!newZoneId.trim()) {
      alert('Please enter a zone ID first');
      return;
    }
    setIsDrawing(true);
    setCurrentPoints([]);
  };

  const addSampleZone = () => {
    if (!newZoneId.trim()) {
      alert('Please enter a zone ID first');
      return;
    }

    // Add a sample rectangular zone
    onAddZone({
      id: newZoneId,
      points: [[100, 100], [300, 100], [300, 200], [100, 200]]
    });

    setNewZoneId('');
  };

  return (
    <div className="zone-config">
      <h3>Zone Configuration</h3>
      
      <div className="zone-input">
        <input
          type="text"
          placeholder="Zone ID (e.g., restricted-area-1)"
          value={newZoneId}
          onChange={(e) => setNewZoneId(e.target.value)}
        />
        <div className="zone-buttons">
          <button onClick={addSampleZone} className="btn-sample">
            Add Sample Zone
          </button>
          <button onClick={startDrawing} className="btn-draw" disabled={isDrawing}>
            {isDrawing ? 'Drawing...' : 'Draw Zone'}
          </button>
          {currentPoints.length > 2 && (
            <button onClick={handleAddZone} className="btn-add">
              Save Zone
            </button>
          )}
        </div>
      </div>

      {isDrawing && (
        <div className="drawing-instructions">
          <p>Click on the video to add points. Need at least 3 points.</p>
          <p>Current points: {currentPoints.length}</p>
        </div>
      )}

      <div className="existing-zones">
        <h4>Active Zones ({zones.length})</h4>
        {zones.length === 0 ? (
          <p>No zones configured</p>
        ) : (
          zones.map(zoneId => (
            <div key={zoneId} className="zone-item">
              <span>{zoneId}</span>
              <button 
                onClick={() => onRemoveZone(zoneId)}
                className="btn-remove"
              >
                Remove
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ZoneConfig;
