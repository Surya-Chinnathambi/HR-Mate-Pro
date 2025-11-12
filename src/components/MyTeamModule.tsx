import { useEffect, useState } from "react";
import apiClient from "../api/client";


interface MyTeamModuleProps {
  employee: any;
}

export function MyTeamModule({ employee }: MyTeamModuleProps) {
  const [teamData, setTeamData] = useState<any | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetch = async () => {
      try {
        const res = await apiClient.get('/realtime/team-summary');
        if (!mounted) return;
        setTeamData(res.data ?? null);
      } catch (err) {
        console.error('Failed to load team data', err);
      }
    };
    fetch();
    return () => { mounted = false; };
  }, []);

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">My Team</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teamData?.team?.map((member: any) => (
          <div key={member._id} className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900">
            <p className="font-semibold text-gray-900 dark:text-white">{member.firstName} {member.lastName}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">{member.designation}</p>
            <p className={`text-sm font-semibold ${member.attendanceStatus === 'Present' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>{member.attendanceStatus}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
