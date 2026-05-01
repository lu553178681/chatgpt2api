"use client";

import { LoaderCircle, PlugZap, Save, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { testProxy, type ProxyTestResult } from "@/lib/api";

import { useSettingsStore } from "../store";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-stone-500">{title}</h3>
      <div className="grid gap-4 md:grid-cols-2">{children}</div>
    </div>
  );
}

export function ConfigCard() {
  const [isTestingProxy, setIsTestingProxy] = useState(false);
  const [proxyTestResult, setProxyTestResult] = useState<ProxyTestResult | null>(null);
  const [webdavExpanded, setWebdavExpanded] = useState(false);
  const logLevelOptions = ["debug", "info", "warning", "error"];
  const config = useSettingsStore((state) => state.config);
  const isLoadingConfig = useSettingsStore((state) => state.isLoadingConfig);
  const isSavingConfig = useSettingsStore((state) => state.isSavingConfig);
  const setRefreshAccountIntervalMinute = useSettingsStore((state) => state.setRefreshAccountIntervalMinute);
  const setImageRetentionDays = useSettingsStore((state) => state.setImageRetentionDays);
  const setTaskTimeoutSeconds = useSettingsStore((state) => state.setTaskTimeoutSeconds);
  const setUploadMaxFileSizeMb = useSettingsStore((state) => state.setUploadMaxFileSizeMb);
  const setImageStorageBackend = useSettingsStore((state) => state.setImageStorageBackend);
  const setWebdavUrl = useSettingsStore((state) => state.setWebdavUrl);
  const setWebdavPublicUrl = useSettingsStore((state) => state.setWebdavPublicUrl);
  const setWebdavUsername = useSettingsStore((state) => state.setWebdavUsername);
  const setWebdavPassword = useSettingsStore((state) => state.setWebdavPassword);
  const setWebdavBasePath = useSettingsStore((state) => state.setWebdavBasePath);
  const setWebdavAuthType = useSettingsStore((state) => state.setWebdavAuthType);
  const setAutoRemoveInvalidAccounts = useSettingsStore((state) => state.setAutoRemoveInvalidAccounts);
  const setAutoRemoveRateLimitedAccounts = useSettingsStore((state) => state.setAutoRemoveRateLimitedAccounts);
  const setLogLevel = useSettingsStore((state) => state.setLogLevel);
  const setProxy = useSettingsStore((state) => state.setProxy);
  const setBaseUrl = useSettingsStore((state) => state.setBaseUrl);
  const saveConfig = useSettingsStore((state) => state.saveConfig);

  const isWebdav = (config?.image_storage_backend || "local") === "webdav";

  const handleTestProxy = async () => {
    const candidate = String(config?.proxy || "").trim();
    if (!candidate) {
      toast.error("请先填写代理地址");
      return;
    }
    setIsTestingProxy(true);
    setProxyTestResult(null);
    try {
      const data = await testProxy(candidate);
      setProxyTestResult(data.result);
      if (data.result.ok) {
        toast.success(`代理可用（${data.result.latency_ms} ms，HTTP ${data.result.status}）`);
      } else {
        toast.error(`代理不可用：${data.result.error ?? "未知错误"}`);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "测试代理失败");
    } finally {
      setIsTestingProxy(false);
    }
  };

  if (isLoadingConfig) {
    return (
      <Card className="rounded-2xl border-white/80 bg-white/90 shadow-sm">
        <CardContent className="flex items-center justify-center p-10">
          <LoaderCircle className="size-5 animate-spin text-stone-400" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-2xl border-white/80 bg-white/90 shadow-sm">
      <CardContent className="space-y-6 p-6">
        <div className="rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm leading-6 text-stone-600">
          管理员登录密钥继续从部署配置读取，不再在此页面展示；如需分发给其他人，请在下方创建普通用户密钥。
        </div>

        {/* 基本设置 */}
        <Section title="基本设置">
          <div className="space-y-2">
            <label className="text-sm text-stone-700">账号刷新间隔</label>
            <Input
              value={String(config?.refresh_account_interval_minute || "")}
              onChange={(event) => setRefreshAccountIntervalMinute(event.target.value)}
              placeholder="分钟"
              className="h-10 rounded-xl border-stone-200 bg-white"
            />
            <p className="text-xs text-stone-500">单位分钟，控制账号自动刷新频率。</p>
          </div>
          <div className="space-y-2">
            <label className="text-sm text-stone-700">全局代理</label>
            <div className="flex gap-2">
              <Input
                value={String(config?.proxy || "")}
                onChange={(event) => {
                  setProxy(event.target.value);
                  setProxyTestResult(null);
                }}
                placeholder="http://127.0.0.1:7890"
                className="h-10 rounded-xl border-stone-200 bg-white"
              />
              <Button
                type="button"
                variant="outline"
                className="h-10 shrink-0 rounded-xl border-stone-200 bg-white px-4 text-stone-700"
                onClick={() => void handleTestProxy()}
                disabled={isTestingProxy}
              >
                {isTestingProxy ? <LoaderCircle className="size-4 animate-spin" /> : <PlugZap className="size-4" />}
                测试
              </Button>
            </div>
            <p className="text-xs text-stone-500">留空表示不使用代理。</p>
            {proxyTestResult ? (
              <div
                className={`rounded-xl border px-3 py-2 text-xs leading-6 ${
                  proxyTestResult.ok
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-rose-200 bg-rose-50 text-rose-800"
                }`}
              >
                {proxyTestResult.ok
                  ? `代理可用：HTTP ${proxyTestResult.status}，用时 ${proxyTestResult.latency_ms} ms`
                  : `代理不可用：${proxyTestResult.error ?? "未知错误"}（用时 ${proxyTestResult.latency_ms} ms）`}
              </div>
            ) : null}
          </div>
          <div className="space-y-2">
            <label className="text-sm text-stone-700">图片访问地址</label>
            <Input
              value={String(config?.base_url || "")}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder="https://example.com"
              className="h-10 rounded-xl border-stone-200 bg-white"
            />
            <p className="text-xs text-stone-500">用于生成图片结果的访问前缀地址。</p>
          </div>
          <div className="space-y-2">
            <label className="text-sm text-stone-700">图片自动清理</label>
            <Input
              value={String(config?.image_retention_days || "")}
              onChange={(event) => setImageRetentionDays(event.target.value)}
              placeholder="30"
              className="h-10 rounded-xl border-stone-200 bg-white"
            />
            <p className="text-xs text-stone-500">自动删除多少天前的本地图片。</p>
          </div>
          <div className="space-y-2">
            <label className="text-sm text-stone-700">任务超时时间</label>
            <Input
              value={String(config?.task_timeout_seconds || "")}
              onChange={(event) => setTaskTimeoutSeconds(event.target.value)}
              placeholder="120"
              className="h-10 rounded-xl border-stone-200 bg-white"
            />
            <p className="text-xs text-stone-500">图片生成/编辑任务的最大执行时间，单位秒，最小 10。</p>
          </div>
          <div className="space-y-2">
            <label className="text-sm text-stone-700">上传文件大小限制</label>
            <Input
              value={String(config?.upload_max_file_size_mb ?? "")}
              onChange={(event) => setUploadMaxFileSizeMb(event.target.value)}
              placeholder="5"
              className="h-10 rounded-xl border-stone-200 bg-white"
            />
            <p className="text-xs text-stone-500">单位 MB，超过此大小的图片将提示压缩。留空或填 0 表示不限制。</p>
          </div>
        </Section>

        {/* 存储设置 */}
        <Section title="存储设置">
          <div className="space-y-2">
            <label className="text-sm text-stone-700">图片存储方式</label>
            <div className="relative">
              <select
                value={config?.image_storage_backend || "local"}
                onChange={(e) => {
                  setImageStorageBackend(e.target.value);
                  if (e.target.value === "webdav") setWebdavExpanded(true);
                }}
                className="h-10 w-full appearance-none rounded-xl border border-stone-200 bg-white px-4 pr-10 text-sm text-stone-700"
              >
                <option value="local">本地存储</option>
                <option value="webdav">WebDAV</option>
              </select>
              <ChevronDown className="pointer-events-none absolute top-3 right-3 size-4 text-stone-400" />
            </div>
            <p className="text-xs text-stone-500">保存即生效，无需重启。</p>
          </div>

          {/* WebDAV 配置 - 可折叠 */}
          {isWebdav && (
            <div className="md:col-span-2">
              <button
                type="button"
                onClick={() => setWebdavExpanded(!webdavExpanded)}
                className="flex items-center gap-1.5 text-sm font-medium text-stone-600 hover:text-stone-900"
              >
                <ChevronRight className={`size-4 transition-transform ${webdavExpanded ? "rotate-90" : ""}`} />
                WebDAV 配置
              </button>
              {webdavExpanded && (
                <div className="mt-3 grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm text-stone-700">WebDAV 地址</label>
                    <Input
                      value={String(config?.webdav_url || "")}
                      onChange={(e) => setWebdavUrl(e.target.value)}
                      placeholder="https://dav.example.com"
                      className="h-10 rounded-xl border-stone-200 bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-stone-700">公开访问地址</label>
                    <Input
                      value={String(config?.webdav_public_url || "")}
                      onChange={(e) => setWebdavPublicUrl(e.target.value)}
                      placeholder="留空则使用 WebDAV 地址"
                      className="h-10 rounded-xl border-stone-200 bg-white"
                    />
                    <p className="text-xs text-stone-500">图片返回给客户端的 URL 前缀。</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-stone-700">存储路径</label>
                    <Input
                      value={String(config?.webdav_base_path || "/images")}
                      onChange={(e) => setWebdavBasePath(e.target.value)}
                      placeholder="/images"
                      className="h-10 rounded-xl border-stone-200 bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-stone-700">认证方式</label>
                    <div className="relative">
                      <select
                        value={config?.webdav_auth_type || "basic"}
                        onChange={(e) => setWebdavAuthType(e.target.value)}
                        className="h-10 w-full appearance-none rounded-xl border border-stone-200 bg-white px-4 pr-10 text-sm text-stone-700"
                      >
                        <option value="basic">Basic</option>
                        <option value="digest">Digest</option>
                      </select>
                      <ChevronDown className="pointer-events-none absolute top-3 right-3 size-4 text-stone-400" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-stone-700">用户名</label>
                    <Input
                      value={String(config?.webdav_username || "")}
                      onChange={(e) => setWebdavUsername(e.target.value)}
                      placeholder="留空表示匿名访问"
                      className="h-10 rounded-xl border-stone-200 bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-stone-700">密码</label>
                    <Input
                      type="password"
                      value={String(config?.webdav_password || "")}
                      onChange={(e) => setWebdavPassword(e.target.value)}
                      placeholder="••••••••"
                      className="h-10 rounded-xl border-stone-200 bg-white"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </Section>

        {/* 高级设置 */}
        <Section title="高级设置">
          <div className="flex flex-col space-y-3 rounded-xl border border-stone-200 bg-white px-4 py-3">
            <h4 className="text-xs font-medium text-stone-500">账号管理</h4>
            <label className="flex items-start gap-3 text-sm text-stone-700">
              <Checkbox
                checked={Boolean(config?.auto_remove_invalid_accounts)}
                onCheckedChange={(checked) => setAutoRemoveInvalidAccounts(Boolean(checked))}
                className="mt-0.5"
              />
              <span>
                自动移除异常账号
                <span className="mt-0.5 block text-xs text-stone-500">Token 失效或账号被封时自动从号池中移除。</span>
              </span>
            </label>
            <label className="flex items-start gap-3 text-sm text-stone-700">
              <Checkbox
                checked={Boolean(config?.auto_remove_rate_limited_accounts)}
                onCheckedChange={(checked) => setAutoRemoveRateLimitedAccounts(Boolean(checked))}
                className="mt-0.5"
              />
              <span>
                自动移除限流账号
                <span className="mt-0.5 block text-xs text-stone-500">触发频率限制时自动从号池中移除，恢复后需手动重新添加。</span>
              </span>
            </label>
          </div>
          <div className="flex flex-col space-y-3 rounded-xl border border-stone-200 bg-white px-4 py-3">
            <h4 className="text-xs font-medium text-stone-500">日志配置</h4>
            <div>
              <label className="text-sm text-stone-700">控制台日志级别</label>
              <p className="mt-1 text-xs text-stone-500">不选择时使用默认 info / warning / error。</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {logLevelOptions.map((level) => (
                <label key={level} className="flex items-center gap-2 text-sm capitalize text-stone-700">
                  <Checkbox
                    checked={Boolean(config?.log_levels?.includes(level))}
                    onCheckedChange={(checked) => setLogLevel(level, Boolean(checked))}
                  />
                  {level}
                </label>
              ))}
            </div>
          </div>
        </Section>

        <div className="flex justify-end">
          <Button
            className="h-10 rounded-xl bg-stone-950 px-5 text-white hover:bg-stone-800"
            onClick={() => void saveConfig()}
            disabled={isSavingConfig}
          >
            {isSavingConfig ? <LoaderCircle className="size-4 animate-spin" /> : <Save className="size-4" />}
            保存
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
