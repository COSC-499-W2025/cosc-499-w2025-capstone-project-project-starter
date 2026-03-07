import React from 'react';

function App() {
  return (
    <div style={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      fontFamily: 'sans-serif'
    }}>
      <h1>Skill Scope</h1>
      <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <button style={{ padding: '10px 20px', fontSize: '16px', minWidth: '200px', cursor: 'pointer' }}>
          Run a New Scan
        </button>
        <button style={{ padding: '10px 20px', fontSize: '16px', minWidth: '200px', cursor: 'pointer' }}>
          Scan Manager
        </button>
      </div>
    </div>
  );
}

export default App;