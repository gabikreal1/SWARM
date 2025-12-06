"use client";

import React from 'react';

const MOCK_JOBS = [
  { id: 101, label: 'Find trendy restaurant in Moscow', status: 'complete', icon: '✅' },
  { id: 102, label: 'TikTok scrape: "trendy restaurants"', status: 'active', icon: '⚡' },
  { id: 103, label: 'Call verification: Sakhalin', status: 'pending', icon: '⏳' },
];

export const JobFeed: React.FC = () => {
  return (
    <div className="card job-feed">
      <div className="card-header">Swarm Activity</div>
      <div className="card-body">
        {MOCK_JOBS.map((job) => (
          <div key={job.id} className="job-row">
            <span className="job-icon">{job.icon}</span>
            <div className="job-main">
              <div className="job-label">{job.label}</div>
              <div className="job-meta">Job #{job.id}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
