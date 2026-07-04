import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { api } from "@/src/api";
import { DishaUser, session } from "@/src/session";
import { colors, spacing } from "@/src/theme";

export default function Splash() {
  const router = useRouter();
  useEffect(() => {
    (async () => {
      const token = await session.getToken();
      if (!token) return router.replace("/login");
      try {
        const res = await api.get<{ ok: boolean; user: DishaUser }>("/auth/me");
        await session.saveUser(res.user);
        router.replace(res.user.purpose ? "/(tabs)" : "/purpose");
      } catch {
        await session.clear();
        router.replace("/login");
      }
    })();
  }, [router]);
  return (
    <LinearGradient colors={[colors.brandDark, colors.brand]} style={styles.wrap}>
      <View style={styles.logo}><Text style={styles.logoT}>D</Text></View>
      <Text style={styles.brand}>DISHA</Text>
      <Text style={styles.tag}>Local Services OS</Text>
      <Text style={styles.tag2}>Powered by ASTRA Technologies</Text>
      <ActivityIndicator color="#FFF" style={{ marginTop: spacing.xl }} />
    </LinearGradient>
  );
}
const styles = StyleSheet.create({ wrap: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl }, logo: { width: 96, height: 96, borderRadius: 48, backgroundColor: "#FFF", alignItems: "center", justifyContent: "center", marginBottom: spacing.lg }, logoT: { fontSize: 54, fontWeight: "900", color: colors.brand }, brand: { color: "#FFF", fontSize: 44, fontWeight: "900", letterSpacing: 2 }, tag: { color: "rgba(255,255,255,0.85)", marginTop: 4 }, tag2: { color: "rgba(255,255,255,0.65)", marginTop: 8, fontSize: 12 } });
