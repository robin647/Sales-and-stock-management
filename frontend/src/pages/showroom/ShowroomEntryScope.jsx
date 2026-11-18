import { useEffect, useState } from "react";
import { showroomApi } from "../../api/endpoints";
import { useAuth } from "../../context/AuthContext";

export default function ShowroomEntryScope({ Page }) {
  const { isAdmin } = useAuth();
  const [showrooms, setShowrooms] = useState([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAdmin) return;
    showroomApi.listAll().then((rows) => {
      setShowrooms(rows);
      setSelected(rows[0]?.id ?? "");
    }).catch(() => setError("Could not load showrooms."));
  }, [isAdmin]);

  if (!isAdmin) return <Page />;

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium">
        Showroom
        <select className="ml-2 rounded-lg border px-3 py-2" value={selected} onChange={(event) => setSelected(event.target.value)}>
          <option value="">Select a showroom</option>
          {showrooms.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
        </select>
      </label>
      {error && <p role="alert">{error}</p>}
      {selected && <Page key={selected} showroomId={selected} />}
    </div>
  );
}
