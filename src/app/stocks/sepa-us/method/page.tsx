import Link from "next/link";

/**
 * 미국 SEPA — 「우리 방법」 정리 페이지.
 *
 * 자료 파일을 «읽지 않는다». 글이 코드에 박힌 정적 페이지다.
 * 글의 출처는 research/handoff/results/262-method-final.md 이고, 미국에 맞는 것만 골라 옮겼다.
 *
 * 토글은 `<details>/<summary>` 로 만든다 — 자바스크립트가 꺼져도 브라우저가 접고 펴기 때문이다.
 * (클라이언트 컴포넌트로 만들면 JS 가 죽은 화면에서 상세 이유가 아예 안 읽힌다.)
 *
 * 겉모습은 ../page.tsx (미국 SEPA 셋업)에 맞췄다. 한국 페이지·컴포넌트는 건드리지 않는다.
 */

export const metadata = {
  title: "우리 방법 — 미국 SEPA",
  description: "무엇을 · 언제 · 얼마나 사고 언제 파는가. 항목마다 까닭을 펼쳐 볼 수 있습니다.",
};

function Toggle({ summary, children }: { summary: string; children: React.ReactNode }) {
  return (
    <details className="group rounded-lg bg-surface-container/30 ghost-border overflow-hidden">
      <summary className="cursor-pointer select-none list-none flex items-center gap-2 px-3 py-2 text-xs font-medium text-on-surface hover:bg-surface-container-high/40 transition-colors [&::-webkit-details-marker]:hidden">
        <span className="material-symbols-outlined text-base text-primary transition-transform group-open:rotate-90">
          chevron_right
        </span>
        <span className="flex-1">{summary}</span>
        <span className="text-[10px] text-on-surface-variant/50 group-open:hidden">펼치기</span>
        <span className="text-[10px] text-on-surface-variant/50 hidden group-open:inline">접기</span>
      </summary>
      <div className="px-3 pt-2 pb-3 border-t border-outline-variant/10 text-xs leading-relaxed text-on-surface-variant space-y-2">
        {children}
      </div>
    </details>
  );
}

function Step({
  no,
  title,
  icon,
  children,
}: {
  no: string;
  title: string;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">{icon}</span>
        <span className="text-on-surface-variant/50 text-sm font-normal">{no}</span>
        {title}
      </h3>
      <div className="bg-surface-container-low rounded-xl ghost-border p-4 space-y-3">{children}</div>
    </section>
  );
}

export default function SepaUsMethodPage() {
  return (
    <div className="space-y-10">
      <header>
        <p className="text-xs mb-2">
          <Link
            href="/stocks/sepa-us"
            className="text-on-surface-variant/60 hover:text-primary transition-colors inline-flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            미국 SEPA 셋업으로
          </Link>
        </p>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">우리 방법</h2>
        <p className="text-base text-on-surface-variant mt-2">
          무엇을 · 언제 · 얼마나 사고 언제 파는가. 항목마다 토글 버튼을 눌러 그렇게 정한 까닭을 펼쳐 볼 수 있습니다.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          이 페이지는 자료 파일을 읽지 않습니다 — 글이 코드에 박혀 있습니다.
        </p>
      </header>

      {/* 1. 무엇을 사는가 */}
      <Step no="1." title="무엇을 사는가" icon="filter_alt">
        <p className="text-sm text-on-surface leading-relaxed">
          추세 판별 8조건을 모두 통과한 미국 종목만 본다. 거기에 적자 종목과 거래가 얇은 종목을 뺀다. 그 안에서 세
          가지 모양(VCP · 파워 플레이 · 3C)을 찾는다.
        </p>

        <div className="space-y-2 pt-1">
          <Toggle summary="8조건">
            <ol className="space-y-1 list-none">
              <li>
                <span className="text-on-surface-variant/50 font-mono mr-2">1</span>종가가 150일선과 200일선 위
              </li>
              <li>
                <span className="text-on-surface-variant/50 font-mono mr-2">2</span>150일선이 200일선 위
              </li>
              <li>
                <span className="text-on-surface-variant/50 font-mono mr-2">3</span>200일선이 최근 한 달 오르는 중
              </li>
              <li>
                <span className="text-on-surface-variant/50 font-mono mr-2">4</span>50일선이 150일선과 200일선 위
              </li>
              <li>
                <span className="text-on-surface-variant/50 font-mono mr-2">5</span>종가가 50일선 위
              </li>
              <li>
                <span className="text-on-surface-variant/50 font-mono mr-2">6</span>종가가 52주 저가보다 30% 이상 위
              </li>
              <li>
                <span className="text-on-surface-variant/50 font-mono mr-2">7</span>종가가 52주 고가에서 25% 안쪽
              </li>
              <li>
                <span className="text-on-surface-variant/50 font-mono mr-2">8</span>상대강도(RS)가 80 이상
              </li>
            </ol>
            <p className="pt-1">
              이 여덟은 미너비니 원전의 조건이다. 우리가 고른 수가 아니다. 27.4년 백테스트가 이 값들로 돌았고, 값이
              바뀌면 그 백테스트가 근거가 되지 못한다. 그래서 값 동결 검산기가 날마다 이 수들을 지킨다.
            </p>
          </Toggle>

          <Toggle summary="적자 제외">
            <p>
              자기자본이익률이 하위인 종목을 뺀다. 27.4년 자료에서 그 무리가 눈에 띄게 나빴다. 다만 이것은 「좋은
              실적을 고른다」가 아니라 「나쁜 실적을 뺀다」다. 둘은 다르다.
            </p>
          </Toggle>

          <Toggle summary="거래가 얇은 종목 제외">
            <p>
              하루 평균 거래대금이 낮으면 뺀다. 살 때도 팔 때도 값이 밀리기 때문이다. 오늘 기준 3,918종목 중
              457종목이 여기서 빠졌다.
            </p>
          </Toggle>

          <Toggle summary="세 가지 모양">
            <p>
              VCP는 출렁임이 점점 줄어드는 모양, 파워 플레이는 짧고 크게 오른 뒤 얕게 쉬는 모양, 3C는 컵 바닥 근처에서
              좁게 눌러앉은 모양이다. 셋 다 미너비니 원전의 모양이고, 우리가 만든 것이 아니다.
            </p>
          </Toggle>
        </div>
      </Step>

      {/* 2. 언제 사는가 */}
      <Step no="2." title="언제 사는가" icon="schedule">
        <p className="text-sm text-on-surface leading-relaxed">
          장이 열리기 전에 피벗 가격으로 자동매수를 예약한다. 장중 거래량은 보지 않는다.
        </p>

        <div className="space-y-2 pt-1">
          <Toggle summary="왜 거래량을 안 보나">
            <p>사용자 본인이 2026-08-23에 정정해 준 방식이다.</p>
            <p>
              거래량이 터질 때는 이미 피벗보다 한참 위라, 본다 해도 예약 주문으로는 집행이 안 된다. 나중에 재보니 그
              판단이 자료로도 맞았다 — 거래량이 3배 이상 터진 날은 갭업이 잦았다(35.4% 대 21.9%). 다만 확인된 것은
              「까닭」이지 「그래서 돈을 번다」가 아니다.
            </p>
          </Toggle>

          <Toggle summary="피벗보다 얼마나 위까지 사나">
            <p>피벗 대비 3.0%까지다. 넘으면 사지 않는다. 추격 매수가 되기 때문이다.</p>
          </Toggle>
        </div>
      </Step>

      {/* 3. 얼마나 사는가 */}
      <Step no="3." title="얼마나 사는가" icon="pie_chart">
        <p className="text-sm text-on-surface leading-relaxed">
          다섯 칸으로 나눠 담는다. 한 거래에서 계좌의 2%까지 잃을 각오를 하고, 한 종목이 계좌의 20%를 넘지 않게 한다.
        </p>

        <div className="space-y-2 pt-1">
          <Toggle summary="왜 다섯 칸인가">
            <p>
              이것은 우리가 직접 재서 나온 셋 중 하나다. 4~5칸이 제일 좋았고 10~15칸으로 늘리면 나빠졌다. 칸을 늘리면
              좋은 종목이 나쁜 종목에 희석되고, 같은 종목이 칸을 겹쳐 먹는다.
            </p>
          </Toggle>

          <Toggle summary="한 칸에 얼마를 넣나">
            <p>
              <span className="font-bold" style={{ color: "#ffb4ab" }}>
                🔴 아직 정하지 않았다.
              </span>{" "}
              지금 코드에 적힌 값은 한국 계좌 기준의 원화 금액이라 미국에 맞지 않는다. 사용자가 계좌 크기를 정하면
              그때 맞춘다.
            </p>
          </Toggle>
        </div>
      </Step>

      {/* 4. 언제 파는가 */}
      <Step no="4." title="언제 파는가" icon="logout">
        <div className="rounded-lg bg-surface-container/30 ghost-border overflow-hidden">
          <table className="w-full text-sm">
            <tbody>
              <tr className="border-b border-outline-variant/10">
                <th
                  scope="row"
                  className="px-3 py-2 text-left font-bold font-mono whitespace-nowrap align-top w-32"
                  style={{ color: "#ffb4ab" }}
                >
                  −10%
                </th>
                <td className="px-3 py-2 text-on-surface">전량 · 반드시 시장가</td>
              </tr>
              <tr className="border-b border-outline-variant/10">
                <th
                  scope="row"
                  className="px-3 py-2 text-left font-bold font-mono whitespace-nowrap align-top"
                  style={{ color: "#34d399" }}
                >
                  +30%
                </th>
                <td className="px-3 py-2 text-on-surface">절반</td>
              </tr>
              <tr className="border-b border-outline-variant/10">
                <th
                  scope="row"
                  className="px-3 py-2 text-left font-bold whitespace-nowrap align-top text-on-surface-variant"
                >
                  그 뒤
                </th>
                <td className="px-3 py-2 text-on-surface">나머지는 25일 저가를 따라 올리는 추격 손절</td>
              </tr>
              <tr>
                <th
                  scope="row"
                  className="px-3 py-2 text-left font-bold whitespace-nowrap align-top text-on-surface-variant"
                >
                  매도 규칙 다섯
                </th>
                <td className="px-3 py-2 text-on-surface">아무것도 팔지 않는다. 점검 표시만 한다</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="space-y-2 pt-1">
          <Toggle summary="왜 손절을 시장가로 하나">
            <p>
              실제 사고 때문이다. 지정가 손절이 체결되지 않아 −5%로 끝났어야 할 거래가 −9.46%가 된 적이 있다. 값을
              지정하면 그 값에 사 줄 사람이 없을 때 그냥 흘러내린다.
            </p>
          </Toggle>

          <Toggle summary="왜 +30%에 절반인가">
            <p>이것도 우리가 직접 재서 나온 셋 중 하나다. 2026-09-02에 +20%에서 +30%으로 바꿨다.</p>
          </Toggle>

          <Toggle summary="왜 25일인가">
            <p>
              <span className="font-bold" style={{ color: "#ffb4ab" }}>
                🔴 모른다.
              </span>{" "}
              원전에도 없고 우리 검정에서 나온 것도 아니다. 출처를 전수로 찾아도 못 찾았다.
            </p>
            <p>
              일곱 값을 격자로 재보니 차이가 뚜렷하지 않았다. 그래서 25를 바꿀 이유가 없다. 25가 좋다는 뜻은 아니다.
            </p>
          </Toggle>

          <Toggle summary="왜 매도 규칙으로 안 파나">
            <p>
              규칙 하나라도 걸리면 바로 파는 방식을 27.4년에 대보니 계좌가 해마다 17.955%p 뒤처졌다. 그 몫을 둘로 갈라
              보면, 자르는 것 <strong className="text-on-surface">자체</strong>가 15.821%p이고 「어디서 자르나」는
              2.133%p인데 뒤엣것은 우리 자로 가릴 수 없었다.
            </p>
            <p>
              그래서 「매도 규칙이 해롭다」고는 쓸 수 없다. 문턱을 하나만 재봤기 때문이다. 확실한 것은 「걸릴 때마다
              바로 파는 것」이 나빴다는 것뿐이다.
            </p>
          </Toggle>
        </div>
      </Step>
    </div>
  );
}
