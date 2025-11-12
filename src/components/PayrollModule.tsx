import { useEffect, useState } from "react";
import apiClient from "../api/client";

interface PayrollModuleProps {
  employee: any;
}

export function PayrollModule({ employee }: PayrollModuleProps) {
  const [payrollRecords, setPayrollRecords] = useState<any[] | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const id = employee?.id ?? employee?._id ?? employee?.employee_id;
        const res = await apiClient.get('/payroll/history', { params: { employee_id: id } });
        if (!mounted) return;
        setPayrollRecords(res.data || []);
      } catch (e) {
        if (!mounted) return;
        setPayrollRecords([]);
      }
    })();
    return () => { mounted = false; };
  }, [employee]);

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-bold mb-4">Payroll History</h2>
      <div className="space-y-4">
        {payrollRecords?.map((record: any) => (
          <div key={record.id ?? record._id} className="flex justify-between items-center p-4 border rounded-lg">
            <div>
              <p className="font-semibold">Pay Period: {record.period}</p>
              <p className="text-sm text-gray-500">Status: Paid</p>
            </div>
            <p className="font-bold text-lg">₹{(record.net_pay ?? record.netPay)?.toLocaleString?.() ?? String(record.net_pay ?? record.netPay)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
