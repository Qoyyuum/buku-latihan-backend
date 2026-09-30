import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { ActivityIndicator, FlatList, Pressable, StyleSheet } from 'react-native';

import { api } from '@/api/client';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';

export default function WorksheetsScreen() {
  const { subject } = useLocalSearchParams<{ subject?: string }>();
  const subjectId = subject ? Number(subject) : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ['worksheets', subjectId],
    queryFn: () => api.worksheets(subjectId),
  });

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: 'Worksheets' }} />
      {isLoading ? (
        <ActivityIndicator style={styles.loader} />
      ) : (
        <FlatList
          data={data?.results ?? []}
          keyExtractor={(w) => String(w.id)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() =>
                router.push(`/(app)/worksheet?id=${item.id}` as never)
              }
            >
              <ThemedText type="smallBold" style={styles.cardTitle}>
                {item.title}
              </ThemedText>
              <ThemedText type="small">
                {item.subject_name}
                {item.exam_year ? ` · ${item.exam_year}` : ''}
                {item.source ? ` · ${item.source}` : ''}
              </ThemedText>
              <ThemedText type="small">
                {item.pages.length} page{item.pages.length === 1 ? '' : 's'}
              </ThemedText>
            </Pressable>
          )}
          ListEmptyComponent={
            <ThemedText type="small" style={styles.empty}>
              No worksheets here yet.
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
    gap: Spacing.half,
  },
  cardTitle: { fontSize: 18 },
  empty: { marginTop: Spacing.five, textAlign: 'center' },
});
