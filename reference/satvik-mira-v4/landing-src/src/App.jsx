import { useEffect, useState } from 'react';
import Hero from './sections/Hero.jsx';
import Categories from './sections/Categories.jsx';
import HowItWorks from './sections/HowItWorks.jsx';
import Honesty from './sections/Honesty.jsx';
import CTA from './sections/CTA.jsx';
import Footer from './sections/Footer.jsx';
import AuthOverlay from './components/AuthOverlay.jsx';

export default function App() {
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState('signup');

  // Deep link from /app when a session/child check fails there — same
  // ?auth=1 contract the old landing.js used (core/auth.js's bounceToSignIn
  // still redirects here with that param; nothing to change server-side).
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('auth') === '1') {
      setAuthTab('signin');
      setAuthOpen(true);
    }
  }, []);

  function openSignup() { setAuthTab('signup'); setAuthOpen(true); }
  function openSignin() { setAuthTab('signin'); setAuthOpen(true); }

  return (
    <div className="min-h-screen bg-bone">
      <Hero onStart={openSignup} onSignIn={openSignin} />
      <Categories />
      <HowItWorks />
      <Honesty />
      <CTA onStart={openSignup} />
      <Footer onSignIn={openSignin} />
      <AuthOverlay open={authOpen} initialTab={authTab} onClose={() => setAuthOpen(false)} />
    </div>
  );
}
