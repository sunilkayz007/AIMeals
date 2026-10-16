import { Stack } from 'expo-router';

export default function MealDetailLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="[logId]" />
    </Stack>
  );
}
