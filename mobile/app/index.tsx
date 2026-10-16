import { Redirect } from 'expo-router';
import { useAuthStore } from '../src/stores/authStore';

export default function Index() {
  const { tokens } = useAuthStore();
  return <Redirect href={tokens?.access_token ? '/(main)/home' : '/(auth)/sign-in'} />;
}