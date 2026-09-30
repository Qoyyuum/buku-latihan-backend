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

export default function MarkingScreen() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['marking-queue'],
    queryFn: () => api.attempts('submitted'),
    refetchInterval: 15_000,
  });
  const { data: graded } = useQuery({
    queryKey: ['marking-queue-graded'],
    queryFn: () => api.attempts('graded'),
  });

  const queue = [...(data?.results ?? []), ...(graded?.results ?? [])];

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: 'Marking queue' }} />
      {isLoading ? (
        <ActivityIndicator style={styles.loader} />
      ) : (
        <FlatList
          data={queue}
          keyExtractor={(a) => String(a.id)}
          refreshing={isLoading}
          onRefresh={refetch}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() =>
                router.push(`/(app)/admin/review?id=${item.id}` as never)
              }
            >
              <View style={styles.row}>
                <View style={styles.grow}>
                  <ThemedText type="smallBold" style={styles.title}>
                    {item.worksheet.title}
                  </ThemedText>
                  <ThemedText type="small">
                    {item.student.username} ·{' '}
                    {item.submitted_at
                      ? new Date(item.submitted_at).toLocaleString()
                      : ''}
                  </ThemedText>
                </View>
                {item.mark?.auto_suggested && (
                  <ThemedText type="small" style={styles.aiBadge}>
                    AI {item.mark.score}/{item.mark.max_score}
                  </ThemedText>
                )}
                {item.status === 'submitted' && (
                  <ThemedText type="small" style={styles.pending}>
                    queued
                  </ThemedText>
                )}
              </View>
            </Pressable>
          )}
          ListEmptyComponent={
            <ThemedText type="small" style={styles.empty}>
              Nothing waiting to be marked.
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
  title: { fontSize: 17 },
  aiBadge: { color: '#7c3aed', fontWeight: '700' },
  pending: { color: '#9aa0aa' },
  empty: { marginTop: Spacing.five, textAlign: 'center' },
});
