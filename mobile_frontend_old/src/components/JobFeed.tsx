import React from 'react';
import { View, Text, ScrollView } from 'react-native';

const MOCK_JOBS = [
  { id: 101, label: 'Find trendy restaurant in Moscow', status: 'complete', icon: '✅' },
  { id: 102, label: 'TikTok scrape: "trendy restaurants"', status: 'active', icon: '⚡' },
  { id: 103, label: 'Call verification: Sakhalin', status: 'pending', icon: '⏳' },
];

export const JobFeed: React.FC = () => {
  return (
    <View
      style={{
        flex: 1,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: '#1f2937',
        backgroundColor: '#020617',
        padding: 12,
      }}
    >
      <Text style={{ color: '#9ca3af', marginBottom: 8 }}>Swarm Activity</Text>
      <ScrollView>
        {MOCK_JOBS.map((job) => (
          <View
            key={job.id}
            style={{
              paddingVertical: 8,
              borderBottomWidth: 1,
              borderBottomColor: '#111827',
              flexDirection: 'row',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <Text style={{ fontSize: 16 }}>{job.icon}</Text>
            <View style={{ flex: 1 }}>
              <Text style={{ color: 'white' }} numberOfLines={1}>
                {job.label}
              </Text>
              <Text style={{ color: '#6b7280', fontSize: 12 }}>Job #{job.id}</Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  );
};
