/** Fixed operational facts and next actions; unknown codes do not imply a cause. */
export function explainDebugFailure(code: string | null, english: boolean): string | null {
  switch (code) {
    case "execution_target_offline":
      return english ? "The selected execution target is offline. Check its connection." : "اتصال اجرای منتخب آفلاین است. اتصال آن را بررسی کنید.";
    case "workspace_capacity_reached":
    case "repository_capacity_reached":
      return english ? "Execution capacity is full. Check free disk and retained repair workspaces." : "ظرفیت فضای اجرای ایجنت پر است. دیسک آزاد و فضای تعمیرهای نگه‌داری‌شده را بررسی کنید.";
    case "exact_release_commit_required":
    case "release_commit_not_available":
      return english ? "The exact failing source is unavailable. Check its release and commit access." : "نسخهٔ دقیق خطادار برای بررسی آماده نیست. شناسهٔ انتشار و دسترسی به commit را بررسی کنید.";
    case "workspace_not_clean":
    case "workspace_identity_mismatch":
    case "workspace_release_mismatch":
    case "workspace_branch_mismatch":
    case "workspace_branch_not_owned":
      return english ? "Workspace identity or changes need review. Existing work was preserved." : "نسخه یا تغییرات فضای کار به بررسی نیاز دارد. کار موجود حفظ شده است.";
    case "interrupted_call_requires_new_run":
      return english ? "The previous execution was interrupted. Review its recorded actions before a new run." : "اجرای قبلی قطع شده است. پیش از شروع دوباره، فعالیت‌های ثبت‌شدهٔ آن را بررسی کنید.";
    case "dedicated_codex_authentication_required":
      return english ? "Independent Codex login is unavailable. Complete the selected runtime's secure login." : "ورود مستقل Codex برقرار نیست. ورود امن همان محل اجرای منتخب را تکمیل کنید.";
    case "unsupported_codex_protocol_version":
      return english ? "This Codex version is not supported by the runtime protocol. Check the pinned executable." : "نسخهٔ Codex با پروتکل این سرویس سازگار نیست. فایل اجرایی با نسخهٔ پشتیبانی‌شده را بررسی کنید.";
    case "dedicated_codex_home_must_be_private":
    case "dedicated_codex_home_configuration_not_allowed":
    case "project_runtime_configuration_not_allowed":
      return english ? "Runtime configuration failed its isolation checks. Review the private configuration without weakening the sandbox." : "تنظیمات اجرا از کنترل جداسازی عبور نکرد. تنظیمات خصوصی را با حفظ محدودیت‌های اجرا بررسی کنید.";
    case "selected_model_not_available":
    case "model_not_configured":
      return english ? "The selected model is unavailable or unset. Verify this exact model in AI Settings." : "مدل منتخب در دسترس نیست یا تنظیم نشده است. همان مدل را در تنظیمات هوش مصنوعی بررسی کنید.";
    case "provider_timeout":
    case "provider_unreachable":
    case "model_capability_discovery_failed":
    case "codex_discovery_failed":
    case "codex_discovery_timeout":
      return english ? "The provider did not respond successfully. Check runtime connectivity and this provider's status." : "پاسخ معتبر از سرویس مدل دریافت نشد. اتصال محل اجرا و وضعیت همان سرویس را بررسی کنید.";
    case "provider_rate_limited":
      return english ? "The provider rate-limited this request. Review its limits before retrying." : "درخواست به محدودیت نرخ سرویس مدل رسیده است. پیش از تلاش دوباره محدودیت همان سرویس را بررسی کنید.";
    case "repair_executor_not_configured":
    case "interactive_runtime_not_configured":
    case "local_connector_not_configured":
      return english ? "A compatible execution runtime is not configured. Select and verify an explicit execution target." : "محیط اجرای سازگار تنظیم نشده است. یک محل اجرای مشخص را انتخاب و اتصالش را بررسی کنید.";
    case "github_credential_not_configured":
      return english ? "Independent GitHub access is not configured. Install the broker's scoped credential in its secret store." : "دسترسی مستقل GitHub تنظیم نشده است. دسترسی محدود broker را در تنظیمات امن آن ثبت کنید.";
    case "github_authorization_rejected":
      return english ? "GitHub rejected the broker's authorization. Check credential validity and scoped repository permissions." : "GitHub دسترسی broker را رد کرده است. اعتبار دسترسی و مجوزهای محدود مخزن را بررسی کنید.";
    case "github_workflow_not_installed":
    case "github_observation_workflow_not_installed":
      return english ? "The required reviewed workflow is unavailable on the trusted branch. Check its release state." : "workflow لازم در شاخهٔ مورداعتماد در دسترس نیست. وضعیت بررسی و انتشار آن را بررسی کنید.";
    case "dispatch_confirmation_missing":
    case "github_mutation_uncertain":
      return english ? "The remote action's result is uncertain. Reconcile its recorded operation before starting another action." : "نتیجهٔ اقدام سمت سرور مشخص نیست. پیش از اقدام دوباره، همان عملیات ثبت‌شده را پیگیری کنید.";
    case "deployment_authorization_expired":
    case "deployment_target_changed":
    case "deployment_preview_changed":
      return english ? "Deployment authorization is stale. Refresh the target and artifact evidence and review a new preview." : "مجوز انتشار به‌روز نیست. شواهد محیط و artifact را تازه کنید و پیش‌نمایش جدید را بررسی کنید.";
    case "deployment_readback_invalid":
      return english ? "The running release could not be verified. Reconcile the exact image and deployment evidence." : "نسخهٔ در حال اجرا تأیید نشد. تصویر دقیق و مدارک انتشار را بررسی کنید.";
    default:
      return null;
  }
}
