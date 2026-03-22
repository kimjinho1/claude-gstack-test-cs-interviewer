import { RadarChart as RechartsRadar, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts'

interface Props { data: { part: string; avg_score: number }[] }

export default function RadarChart({ data }: Props) {
  if (!data.length) return <div className="text-gray-500 text-sm text-center py-8">데이터가 없습니다.</div>
  return (
    <ResponsiveContainer width="100%" height={260}>
      <RechartsRadar data={data}>
        <PolarGrid stroke="#374151" />
        <PolarAngleAxis dataKey="part" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
        <Radar dataKey="avg_score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
      </RechartsRadar>
    </ResponsiveContainer>
  )
}
