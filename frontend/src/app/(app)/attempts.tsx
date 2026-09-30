import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Stack } from 'expo-router/stack';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';

import { api } from '@/api/client';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/auth/store';

const STATUS_LABEL: Record<string, string> = {
  in_progress: 'In progress',
  submitted: 'Submitted — marking…',
  grading: 'Auto-grading…',
  graded: 'Marked — being reviewed',
  returned: 'Returned',
};

export default function AttemptsScreen() {
  const { isStudent } = useAuth();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['attempts'],
    queryFn: () => api.attempts(),
    refetchInterval: 15_000,
  });

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: 'Attempts' }} />
      {isLoading ? (
        <ActivityIndicator style={styles.loader} />
      ) : (
        <FlatList
          data={data?.results ?? []}
          keyExtractor={(a) => String(a.id)}
          refreshing={isLoading}
          onRefresh={refetch}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() => {
                if (item.status === 'in_progress' && isStudent) {
                  router.push(`/(app)/worksheet?id=${item.worksheet.id}` as never);
                }
              }}
            >
              <View style={styles.row}>
                <View style={styles.grow}>
                  <ThemedText type="smallBold" style={styles.cardTitle}>
                    {item.worksheet.title}
                  </ThemedText>
                  <ThemedText type="small">
                    {STATUS_LABEL[item.status] ?? item.status}
                    {' · '}
                    {new Date(item.started_at).toLocaleDateString()}
                  </ThemedText>
                </View>
                {item.status === 'returned' && item.mark && (
                  <ThemedText type="smallBold" style={styles.score}>
                    {item.mark.score}/{item.mark.max_score}
                  </ThemedText>
                )}
              </View>
              {item.status === 'returned' && !!item.mark?.feedback && (
                <ThemedText type="small" style={styles.feedback}>
                  {item.mark.feedback}
                </ThemedText>
              )}
            </Pressable>
          )}
          ListEmptyComponent={
            <ThemedText type="small" style={styles.empty}>
              No attempts yet — pick a subject and start a worksheet.
            </ThemedText>
          }
        />
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: Spacing.three },
  loader: { marginTop: Spacing.five },
  list: { gap: Spacing.two },
  card: {
    padding: Spacing.three,
    borderRadius: 10,
    backgroundColor: '#E0E1E6',
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  grow: { flex: 1 },
  cardTitle: { fontSize: 18 },
  score: { fontSize: 18, color: '#208AEF' },
  feedback: { marginTop: Spacing.two, opacity: 0.8 },
  empty: { marginTop: Spacing.five, textAlign: 'center' },
});
