import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
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

export default function SubjectsScreen() {
  const { user, isTeacher, logout } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: ['subjects'],
    queryFn: api.subjects,
  });

  return (
    <ThemedView style={styles.container}>
      <View style={styles.header}>
        <View>
          <ThemedText type="title">Subjects</ThemedText>
          <ThemedText type="small">
            Signed in as {user?.username} ({user?.role})
          </ThemedText>
        </View>
        <Pressable onPress={logout}>
          <ThemedText type="link">Sign out</ThemedText>
        </Pressable>
      </View>

      <View style={styles.navRow}>
        <Pressable onPress={() => router.push('/(app)/attempts')}>
          <ThemedText type="link">My attempts</ThemedText>
        </Pressable>
        <Pressable onPress={() => router.push('/(app)/dashboard')}>
          <ThemedText type="link">Dashboard</ThemedText>
        </Pressable>
        {isTeacher && (
          <Pressable onPress={() => router.push('/(app)/admin/upload')}>
            <ThemedText type="link">Upload worksheet</ThemedText>
          </Pressable>
        )}
        {isTeacher && (
          <Pressable onPress={() => router.push('/(app)/admin/marking')}>
            <ThemedText type="link">Marking queue</ThemedText>
          </Pressable>
        )}
      </View>

      {isLoading ? (
        <ActivityIndicator style={styles.loader} />
      ) : (
        <FlatList
          data={data?.results ?? []}
          keyExtractor={(s) => String(s.id)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() =>
                router.push(`/(app)/worksheets?subject=${item.id}` as never)
              }
            >
              <ThemedText type="smallBold" style={styles.cardTitle}>
                {item.name}
              </ThemedText>
              {!!item.description && (
                <ThemedText type="small">{item.description}</ThemedText>
              )}
            </Pressable>
          )}
        />
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: Spacing.three },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  navRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.three,
    marginVertical: Spacing.three,
  },
  loader: { marginTop: Spacing.five },
  list: { gap: Spacing.two },
  card: {
    padding: Spacing.three,
    borderRadius: 10,
    backgroundColor: '#E0E1E6',
  },
  cardTitle: { fontSize: 18 },
});
