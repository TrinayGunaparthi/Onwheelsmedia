import { useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
export default function BulkImport() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!file) return;
    setBusy(true); setResult(null);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/admin/drivers/bulk", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(data); toast.success(`Imported ${data.imported} drivers`);
    } catch (e) { toast.error(e.response?.data?.detail || "Import failed"); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid="admin-bulk" className="max-w-2xl space-y-4">
      <div className="border border-zinc-800 p-6">
        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-3">CSV format</div>
        <pre className="bg-zinc-900 border border-zinc-800 p-3 text-xs font-mono overflow-x-auto rounded">
email,password,full_name,phone,address,city,state,vehicle_reg_no,vehicle_type,manufacturer,model,year,color,operating_area,preferred_routes
raj@example.com,Owm@12345,Raj Kumar,9999999999,MG Rd,Bangalore,KA,KA-01-A-1234,Auto Rickshaw,Bajaj,RE,2022,Yellow-Green,Indiranagar,MG Road-Whitefield
        </pre>
        <div className="mt-4">
          <input data-testid="bulk-file" type="file" accept=".csv" onChange={e => setFile(e.target.files[0])} className="text-sm text-zinc-400" />
        </div>
        <button data-testid="bulk-submit" onClick={submit} disabled={!file || busy} className="mt-4 bg-yellow-400 hover:bg-yellow-300 disabled:opacity-40 text-zinc-950 px-6 py-3 rounded font-semibold">
          {busy ? "Importing…" : "Import drivers"}
        </button>
      </div>
      {result && (
        <div className="border border-zinc-800 p-4" data-testid="bulk-result">
          <div className="text-green-400 font-medium">✓ Imported {result.imported} drivers</div>
          {result.failed_count > 0 && (
            <div className="mt-2">
              <div className="text-red-400 text-sm">{result.failed_count} rows failed:</div>
              <div className="text-xs font-mono text-zinc-500 mt-1">
                {result.failed.map((f, i) => <div key={i}>Row {f.row}: {f.reason}</div>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
