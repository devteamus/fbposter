"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Upload, Pause, Play, Trash2, Eye, Loader2 } from "lucide-react";

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedJob, setSelectedJob] = useState<any>(null);
  const [posts, setPosts] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);

  const load = () => {
    Promise.all([api.listJobs(), api.listAccounts()])
      .then(([j, a]) => { setJobs(j); setAccounts(a); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const formData = new FormData(form);
    setUploading(true);
    try {
      await api.uploadCSV(formData);
      setShowUpload(false);
      load();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUploading(false);
      form.reset();
    }
  };

  const viewPosts = async (job: any) => {
    setSelectedJob(job);
    const p = await api.getJobPosts(job.id);
    setPosts(p);
  };

  const toggleJob = async (job: any) => {
    if (job.status === "running") await api.pauseJob(job.id);
    else if (job.status === "paused") await api.resumeJob(job.id);
    load();
  };

  const deleteJob = async (id: number) => {
    if (!confirm("Delete this job and all its posts?")) return;
    await api.deleteJob(id);
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Jobs</h1>
          <p className="text-sm text-muted-foreground">Manage your bulk posting campaigns</p>
        </div>
        <button onClick={() => setShowUpload(!showUpload)}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          <Upload className="h-4 w-4" />
          Upload CSV
        </button>
      </div>

      {showUpload && (
        <form onSubmit={handleUpload} encType="multipart/form-data" className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold">New bulk post job</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Account</label>
              <select name="account_id" required className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <option value="">Select page</option>
                {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Interval value</label>
              <input name="interval_value" type="number" min={1} defaultValue={2} required
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Unit</label>
              <select name="interval_unit" className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <option value="minutes">Minutes</option>
                <option value="hours">Hours</option>
                <option value="days">Days</option>
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">CSV file</label>
            <input name="csv" type="file" accept=".csv" required
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm file:mr-4 file:rounded file:border-0 file:bg-primary file:px-2 file:py-1 file:text-xs file:text-primary-foreground" />
            <p className="text-xs text-muted-foreground">Columns required: caption, media_url. Optional: post_type (image/video), comment (auto-posted as a comment after the post goes live)</p>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={uploading} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Start job"}
            </button>
            <button type="button" onClick={() => setShowUpload(false)} className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted">Cancel</button>
          </div>
        </form>
      )}

      <div className="rounded-xl border bg-card shadow-sm overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-6 py-3 text-left font-medium text-muted-foreground">File</th>
              <th className="px-6 py-3 text-left font-medium text-muted-foreground">Account</th>
              <th className="px-6 py-3 text-left font-medium text-muted-foreground">Progress</th>
              <th className="px-6 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th className="px-6 py-3 text-right font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">Loading...</td></tr>
            ) : jobs.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">No jobs yet.</td></tr>
            ) : (
              jobs.map((job) => (
                <tr key={job.id} className="hover:bg-muted/30">
                  <td className="px-6 py-4">
                    <p className="font-medium">{job.original_filename}</p>
                    <p className="text-xs text-muted-foreground">{new Date(job.created_at).toLocaleString()}</p>
                  </td>
                  <td className="px-6 py-4 text-muted-foreground">{job.account_name}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="h-2 w-24 overflow-hidden rounded-full bg-muted">
                        <div className="h-full bg-green-500 transition-all" style={{ width: `${job.total_posts ? (job.completed_posts / job.total_posts) * 100 : 0}%` }} />
                      </div>
                      <span className="text-xs text-muted-foreground">{job.completed_posts}/{job.total_posts}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4"><StatusBadge status={job.status} /></td>
                  <td className="px-6 py-4">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => viewPosts(job)} className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground" title="View posts"><Eye className="h-4 w-4" /></button>
                      {(job.status === "running" || job.status === "paused") && (
                        <button onClick={() => toggleJob(job)} className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground" title={job.status === "running" ? "Pause" : "Resume"}>
                          {job.status === "running" ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                        </button>
                      )}
                      <button onClick={() => deleteJob(job.id)} className="rounded-lg p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive" title="Delete"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-xl border bg-card p-6 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Posts: {selectedJob.original_filename}</h3>
              <button onClick={() => { setSelectedJob(null); setPosts([]); }} className="rounded-lg p-2 hover:bg-muted">✕</button>
            </div>
            <div className="space-y-2">
              {posts.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-lg border p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{p.caption}</p>
                    <p className="truncate text-xs text-muted-foreground">{p.media_url}</p>
                    {p.comment && (
                      <p className="mt-1 truncate text-xs">
                        <span className="text-muted-foreground">Comment: </span>
                        <span className={p.comment_posted ? "text-green-600" : p.status === "posted" ? "text-red-600" : "text-muted-foreground"}>
                          {p.comment}
                          {p.status === "posted" && (p.comment_posted ? " ✓" : " (failed to post)")}
                        </span>
                      </p>
                    )}
                  </div>
                  <span className={`ml-4 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                    p.status === "posted" ? "bg-green-100 text-green-700" :
                    p.status === "failed" ? "bg-red-100 text-red-700" :
                    p.status === "scheduled" ? "bg-blue-100 text-blue-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>{p.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    running: "bg-blue-100 text-blue-700",
    paused: "bg-gray-100 text-gray-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${map[status] || map.pending}`}>
      {status}
    </span>
  );
}
