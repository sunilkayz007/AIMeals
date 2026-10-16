import { Stack } from 'expo-router';

export default function MealPlansLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="new" />
      <Stack.Screen name="[planId]" />
    </Stack>
  );
}
