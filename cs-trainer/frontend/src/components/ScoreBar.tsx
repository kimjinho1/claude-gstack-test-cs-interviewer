interface Props { score: number }
export default function ScoreBar({ score }: Props) {
  const color = score >= 7 ? 'bg-green-500' : score >= 4 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-700 rounded-full h-3">
        <div className={`${color} h-3 rounded-full transition-all`} style={{ width: `${score * 10}%` }} />
      </div>
      <span className={`font-bold text-lg w-8 ${score >= 7 ? 'text-green-400' : score >= 4 ? 'text-yellow-400' : 'text-red-400'}`}>
        {score}
      </span>
    </div>
  )
}
