import React from 'react';
import './ProgressIndicator.scss';

function ProgressIndicator({
  type = 'spinner',
  progress = 0,
  message = 'Loading...',
  size = 'medium',
  color = 'primary'
}) {
  if (type === 'bar') {
    return (
      <div className={`progress-bar-container ${size}`}>
        <div className="progress-message">{message}</div>
        <div className="progress-bar">
          <div
            className={`progress-fill ${color}`}
            style={{ width: `${progress}%` }}
          >
            {progress > 0 && <span className="progress-text">{progress}%</span>}
          </div>
        </div>
      </div>
    );
  }

  if (type === 'circular') {
    const radius = size === 'small' ? 20 : size === 'large' ? 60 : 40;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (progress / 100) * circumference;

    return (
      <div className={`circular-progress ${size}`}>
        <svg width={radius * 2 + 10} height={radius * 2 + 10}>
          <circle
            className="progress-circle-bg"
            cx={radius + 5}
            cy={radius + 5}
            r={radius}
            strokeWidth="4"
          />
          <circle
            className={`progress-circle ${color}`}
            cx={radius + 5}
            cy={radius + 5}
            r={radius}
            strokeWidth="4"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
          />
        </svg>
        <div className="progress-content">
          <div className="progress-value">{progress}%</div>
          <div className="progress-label">{message}</div>
        </div>
      </div>
    );
  }

  // Default: spinner
  return (
    <div className={`spinner-container ${size}`}>
      <div className={`spinner ${color}`}>
        <div className="spinner-blade"></div>
        <div className="spinner-blade"></div>
        <div className="spinner-blade"></div>
        <div className="spinner-blade"></div>
        <div className="spinner-blade"></div>
        <div className="spinner-blade"></div>
        <div className="spinner-blade"></div>
        <div className="spinner-blade"></div>
      </div>
      <div className="spinner-message">{message}</div>
    </div>
  );
}

export default ProgressIndicator;