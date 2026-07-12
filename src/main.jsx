import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import "@fontsource-variable/fraunces";
import "@fontsource-variable/work-sans";
import "@fontsource-variable/jetbrains-mono";
import "./styles/bench/tokens.css";
import "./styles/bench/base.css";
import './styles/index.scss';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);