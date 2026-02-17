// Version 1 without tailwind
/*
import React from 'react';


const Sidebar = ({ transparency, setTransparency }) => {
  return (
    <div style={{ width: '300px', background: '#f8f9fa', padding: '1rem', borderRight: '1px solid #ddd' }}>
      <h2>BW Geoportal</h2>
      <hr />
      <div style={{ marginTop: '20px' }}>
        <label>Layer Transparency: {transparency}%</label>
        <input 
          type="range" 
          min="0" max="100" 
          value={transparency} 
          onChange={(e) => setTransparency(e.target.value)}
          style={{ width: '100%' }}
        />
      </div>
    </div>
  );
};

export default Sidebar;
*/


// Version 2: Tailwind
import React from 'react';
// We will use Lucide for icons (part of the packages installed)
import { Layers, Settings2 } from 'lucide-react';

const Sidebar = ({ transparency, setTransparency }) => {
  return (
    <aside className="w-80 bg-slate-900 text-slate-100 h-screen flex flex-col shadow-xl z-10">
      {/* Header */}
      <div className="p-6 border-b border-slate-700 flex items-center gap-3">
        <Layers className="text-blue-400" />
        <h1 className="text-xl font-bold tracking-tight">BW Geoportal</h1>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-8">
        <div>
          <div className="flex items-center gap-2 mb-4 text-slate-400">
            <Settings2 size={18} />
            <span className="text-sm font-semibold uppercase tracking-wider">Map Controls</span>
          </div>
          
          <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
            <label className="block text-sm font-medium mb-3">
              Base Layer Transparency
            </label>
            <input 
              type="range" 
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              min="0" max="100" 
              value={transparency} 
              onChange={(e) => setTransparency(e.target.value)}
            />
            <div className="flex justify-between text-xs text-slate-500 mt-2 font-mono">
              <span>0%</span>
              <span>{transparency}%</span>
              <span>100%</span>
            </div>
          </div>
        </div>

        {/* Future placeholder for your 450 layers */}
        <div className="opacity-50 border-t border-slate-800 pt-6">
          <p className="text-xs italic text-slate-500 text-center">
            Layer list initialization...
          </p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;