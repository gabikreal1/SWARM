import React from 'react';
import { View, Text, SafeAreaView } from 'react-native';
import { ButlerSphere } from '../src/components/ButlerSphere';
import { JobFeed } from '../src/components/JobFeed';
import { WalletConnectPanel } from '../src/features/wallet/WalletConnectPanel';

export default function HomeScreen() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#020617' }}>
      <View style={{ flex: 1, padding: 16, gap: 16 }}>
        <View style={{ flex: 3 }}>
          <ButlerSphere />
        </View>
        <View style={{ flex: 2 }}>
          <JobFeed />
        </View>
        <View style={{ flex: 1 }}>
          <WalletConnectPanel />
        </View>
      </View>
    </SafeAreaView>
  );
}
