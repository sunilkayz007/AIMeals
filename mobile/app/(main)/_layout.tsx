import { Stack } from 'expo-router';

export default function MainLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="home" />
      <Stack.Screen name="settings" />
      <Stack.Screen name="pantry" />
      <Stack.Screen name="recipes" />
      <Stack.Screen name="allergies" />
      <Stack.Screen name="coach" />
      <Stack.Screen name="credits" />
      <Stack.Screen name="goals" />
      <Stack.Screen name="achievements" />
    </Stack>
  );
}
