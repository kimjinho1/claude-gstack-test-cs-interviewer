import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface Props { data: { week: string; avg_score: number }[] }

export default function TrendChart({ data }: Props) {
  if (!data.length) return <div className="text-gray-500 text-sm text-center py-8">데이터가 없습니다.</div>
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="week" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
        <YAxis domain={[0, 10]} tick={{ fill: '#9CA3AF', fontSize: 11 }} />
        <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
        <Line type="monotone" dataKey="avg_score" stroke="#6366f1" strokeWidth={2} dot={{ fill: '#6366f1' }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
