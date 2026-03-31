import { useState } from 'react';
import { Copy, Check, Terminal, GitBranch, Code, Rocket, ChevronDown, ChevronRight } from 'lucide-react';
import Header from '../components/layout/Header';

function CopyBlock({ label, command }: { label?: string; command: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      {label && <div className="px-3 py-1.5 bg-gray-800 text-xs text-gray-400">{label}</div>}
      <div className="flex items-center justify-between px-3 py-2">
        <code className="text-sm text-green-400 font-mono">{command}</code>
        <button onClick={handleCopy} className="ml-3 text-gray-500 hover:text-white flex-shrink-0">
          {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
        </button>
      </div>
    </div>
  );
}

function Step({ number, title, icon: Icon, children, defaultOpen = false }: {
  number: number; title: string; icon: typeof Terminal; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-gray-50">
        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
          {number}
        </div>
        <Icon size={18} className="text-gray-500 flex-shrink-0" />
        <span className="font-semibold text-gray-800 flex-1">{title}</span>
        {open ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
      </button>
      {open && <div className="px-4 pb-4 space-y-3 border-t">{children}</div>}
    </div>
  );
}

export default function GuidePage() {
  const serverIP = window.location.hostname;
  const repoPath = '/srv/repos/SMAgentLab.git';

  return (
    <div>
      <Header title="시작 가이드" subtitle="프로젝트 세팅부터 배포까지 단계별 안내" />

      <div className="max-w-3xl space-y-4">
        <Step number={1} title="회원가입 & 승인" icon={Code} defaultOpen>
          <p className="text-sm text-gray-600 mt-3">이미 로그인되어 있다면 이 단계는 완료된 것입니다.</p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
            회원가입 → 관리자 승인 대기 → 승인 후 로그인 → 설정에서 LLM API Key 등록
          </div>
        </Step>

        <Step number={2} title="프로젝트 클론 (최초 1회)" icon={Terminal}>
          <p className="text-sm text-gray-600 mt-3">VSCode 터미널에서 아래 명령어를 실행하세요.</p>
          <CopyBlock label="프로젝트 클론" command={`git clone ssh://user@${serverIP}${repoPath}`} />
          <CopyBlock label="폴더 이동" command="cd SMAgentLab" />
          <CopyBlock label="VSCode로 열기" command="code ." />
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
            <strong>참고:</strong> SSH 계정은 서버 관리자에게 요청하세요. 최초 1회만 하면 됩니다.
          </div>
        </Step>

        <Step number={3} title="브랜치 생성" icon={GitBranch}>
          <p className="text-sm text-gray-600 mt-3">
            포탈의 <strong>브랜치 관리</strong> 페이지에서 생성하세요.
          </p>
          <div className="bg-gray-50 rounded-lg p-3 text-sm">
            <p>1. 사이드바 → <strong>브랜치 관리</strong></p>
            <p>2. 기준 브랜치: <code className="bg-gray-200 px-1 rounded">main</code> 선택</p>
            <p>3. 새 브랜치 이름 입력 (예: <code className="bg-gray-200 px-1 rounded">feature/my-feature</code>)</p>
            <p>4. <strong>생성</strong> 클릭</p>
          </div>
        </Step>

        <Step number={4} title="브랜치 전환 & 개발" icon={Code}>
          <p className="text-sm text-gray-600 mt-3">VSCode 터미널에서 브랜치를 전환하고 개발하세요.</p>
          <CopyBlock label="원격 브랜치 가져오기" command="git fetch" />
          <CopyBlock label="브랜치 전환" command="git checkout feature/my-feature" />
          <div className="bg-gray-50 rounded-lg p-3 text-sm">
            <p className="font-medium mb-1">코드 수정 후:</p>
          </div>
          <CopyBlock label="변경 파일 추가" command="git add ." />
          <CopyBlock label="커밋" command='git commit -m "feat: 기능 설명"' />
          <CopyBlock label="푸쉬" command="git push origin feature/my-feature" />
          <div className="bg-gray-50 rounded-lg p-3 text-sm mt-2">
            <p className="font-medium mb-1">커밋 메시지 규칙:</p>
            <div className="grid grid-cols-2 gap-1 text-xs font-mono">
              <span><strong>feat:</strong> 새 기능</span>
              <span><strong>fix:</strong> 버그 수정</span>
              <span><strong>chore:</strong> 설정/기타</span>
              <span><strong>refactor:</strong> 리팩터링</span>
              <span><strong>docs:</strong> 문서</span>
              <span><strong>test:</strong> 테스트</span>
            </div>
          </div>
        </Step>

        <Step number={5} title="코드 리뷰 & 승인" icon={Code}>
          <p className="text-sm text-gray-600 mt-3">포탈에서 변경사항을 확인하고 승인받으세요.</p>
          <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
            <p>1. 사이드바 → <strong>코드 리뷰</strong></p>
            <p>2. 브랜치 선택 → 변경 파일 / Diff 확인</p>
            <p>3. <strong>AI 영향도 분석</strong> 또는 <strong>AI 코드 리뷰</strong> 실행 (선택)</p>
            <p>4. 리뷰어에게 <strong>승인</strong> 요청</p>
          </div>
        </Step>

        <Step number={6} title="배포" icon={Rocket}>
          <p className="text-sm text-gray-600 mt-3">승인된 브랜치를 배포합니다.</p>
          <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
            <p>1. 사이드바 → <strong>배포</strong></p>
            <p>2. 승인된 브랜치 선택 → 변경사항 확인</p>
            <p>3. <strong>배포 실행</strong> 클릭</p>
            <p>4. 실시간 빌드 로그 확인</p>
            <p>5. 성공 시 → main 자동 머지 + Docker 재기동</p>
            <p>6. 실패 시 → AI 원인 분석 + 원복 가능</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            <strong>주의:</strong> main 브랜치에 직접 push 하지 마세요. 반드시 브랜치 → 리뷰 → 배포 경로를 따르세요.
          </div>
        </Step>

        <Step number={7} title="설정" icon={Code}>
          <p className="text-sm text-gray-600 mt-3">개인 설정을 관리합니다.</p>
          <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
            <p>• 사이드바 하단 <strong>톱니바퀴</strong> → LLM API Key 등록, 비밀번호 변경</p>
            <p>• AI 영향도 분석, 코드 리뷰, 실패 분석을 사용하려면 API Key가 필요합니다</p>
          </div>
        </Step>
      </div>
    </div>
  );
}
