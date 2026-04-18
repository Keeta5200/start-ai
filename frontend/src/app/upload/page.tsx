import { AppShell } from "@/components/app-shell";
import { UploadForm } from "@/components/upload-form";

export default function UploadPage() {
  return (
    <AppShell
      title="動画アップロード"
      subtitle="スタート局面の動画を受け取り、メタデータ保存と解析ジョブの開始までを行います。"
    >
      <UploadForm />
    </AppShell>
  );
}
