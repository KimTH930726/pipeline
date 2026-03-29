import type { FileChange } from '../../types/git';

interface Props {
  files: FileChange[];
  selectedPath?: string;
  onSelect: (path: string) => void;
}

const statusColors: Record<string, string> = {
  A: 'bg-green-100 text-green-700',
  M: 'bg-yellow-100 text-yellow-700',
  D: 'bg-red-100 text-red-700',
  R: 'bg-blue-100 text-blue-700',
};

export default function ChangedFileList({ files, selectedPath, onSelect }: Props) {
  if (!files.length) {
    return <p className="text-sm text-gray-400 p-3">변경된 파일 없음</p>;
  }

  return (
    <ul className="divide-y divide-gray-200">
      {files.map((f) => (
        <li
          key={f.path}
          onClick={() => onSelect(f.path)}
          className={`flex items-center gap-2 px-3 py-2 cursor-pointer text-sm hover:bg-gray-50 transition-colors ${
            selectedPath === f.path ? 'bg-blue-50' : ''
          }`}
        >
          <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${statusColors[f.status] || 'bg-gray-100'}`}>
            {f.status}
          </span>
          <span className="truncate">{f.path}</span>
        </li>
      ))}
    </ul>
  );
}
