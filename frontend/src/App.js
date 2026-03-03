import React from 'react';
import './App.css';
import Homepage from './Homepage.jsx';
import PublicPortfolioView from './PublicPortfolioView.jsx';

function getPublicSlugFromPath(pathname) {
  const match = String(pathname || '').match(/^\/portfolio\/([a-zA-Z0-9_-]+)\/?$/);
  return match ? match[1] : null;
}

function App() {
  const publicSlug = getPublicSlugFromPath(window.location.pathname);
  if (publicSlug) {
    return <PublicPortfolioView publicSlug={publicSlug} />;
  }

  return (
    <div>
      <Homepage />
    </div>
  );
}

export default App;
