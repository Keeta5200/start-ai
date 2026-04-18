export function ResultCard({
  title,
  value,
  subtitle,
  accent = false
}: {
  title: string;
  value: string | number;
  subtitle: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-[1.75rem] border p-5 transition ${
        accent
          ? "border-ember/40 bg-gradient-to-br from-ember/15 to-white/[0.03]"
          : "border-white/10 bg-white/[0.04]"
      }`}
    >
      <p className="text-xs uppercase tracking-[0.3em] text-fog">{title}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-sm leading-6 text-fog">{subtitle}</p>
    </div>
  );
}
