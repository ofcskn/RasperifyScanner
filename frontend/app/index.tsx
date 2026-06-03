import { Redirect } from 'expo-router';
import { isAuthenticated } from '../services/api';

export default function Root() {
  return <Redirect href={isAuthenticated() ? '/(tabs)' : '/login'} />;
}
