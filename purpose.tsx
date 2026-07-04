import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text } from "react-native";
import { api, apiErrorText } from "@/src/api";
import { Purpose, DishaUser, session } from "@/src/session";
import { colors, spacing } from "@/src/theme";
import { Card, ErrorBox } from "@/src/ui";

export default function PurposeScreen() {
  const router = useRouter();
  const [error, setError] = useState("");
  async function choose(purpose: Purpose) {
    try {
      setError("");
      const res = await api.patch<{ ok: boolean; user: DishaUser }>("/auth/purpose", { purpose });
      await session.saveUser(res.user);
      router.replace(purpose === "TAKER" ? "/(tabs)" : "/provider-setup");
    } catch (e) { setError(apiErrorText(e)); }
  }
  return (
    <ScrollView contentContainerStyle={styles.wrap}>
      <Text style={styles.title}>আপনি কী করতে চান?</Text>
      {!!error && <ErrorBox message={error} />}
      <PurposeCard icon="🔍" title="পরিষেবা নিতে চাই" sub="Provider খুঁজব, booking করব, chat করব" onPress={() => choose("TAKER")} />
      <PurposeCard icon="🛠️" title="পরিষেবা দিতে চাই" sub="নিজের service listing তৈরি করব" onPress={() => choose("PROVIDER")} />
      <PurposeCard icon="🔁" title="দুটোই" sub="একই account থেকে provider ও customer" onPress={() => choose("BOTH")} />
    </ScrollView>
  );
}
function PurposeCard({ icon, title, sub, onPress }: { icon: string; title: string; sub: string; onPress: () => void }) {
  return <Pressable onPress={onPress}><Card><Text style={styles.icon}>{icon}</Text><Text style={styles.ct}>{title}</Text><Text style={styles.cs}>{sub}</Text></Card></Pressable>;
}
const styles = StyleSheet.create({ wrap: { flexGrow: 1, padding: spacing.xl, gap: spacing.lg, justifyContent: "center", backgroundColor: colors.surface }, title: { fontSize: 26, fontWeight: "900", color: colors.text }, icon: { fontSize: 34 }, ct: { fontSize: 18, fontWeight: "900", color: colors.text, marginTop: 8 }, cs: { color: colors.muted, marginTop: 4 } });
