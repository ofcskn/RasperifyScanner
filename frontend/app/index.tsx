import { Redirect } from 'expo-router';
import { View, ActivityIndicator } from 'react-native';
import { useAuth } from '../context/AuthContext';

export default function Root() {
  const { isAuthenticated, isLoading } = useAuth();

  // Show a blank loading screen while AsyncStorage restores the session.
  if (isLoading) {
    return (
      <View style={{ flex: 1, backgroundColor: '#f0f4f8', justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  return <Redirect href={isAuthenticated ? '/(tabs)' : '/login'} />;
}
