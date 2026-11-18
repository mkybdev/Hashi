import { expect, test } from 'bun:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { PlayScreen } from '../src/game/screens';
import { defaults, type Feedback, type State, type Word } from '../src/game/engine';

const target: Word = { id:1, text:'優位', reading:'ユウイ', key:'優位:ユウイ', accents:[1], pitch_patterns:[[2,1,1]], accent_pattern:[2,1,1], source:'kanjium', estimated:false, mora_count:3 };
const feedback: Feedback = {correct:true, message:'正解！同じ高低のリズムです。', target, answer:{...target,id:2,text:'周囲',reading:'シュウイ',key:'周囲:シュウイ'}};
function render(finished: State['finished']) {
  const game = {settings:{...defaults,mode:'timeAttack' as const,targetCount:1},setSettings:()=>{},target,feedback,history:[feedback],loading:false,error:'',elapsed:500,finished,load:async()=>{},guess:async()=>{},cancel:()=>{}};
  return renderToStaticMarkup(<PlayScreen game={game} next={async()=>{}} leave={()=>{}} correct={1} input="周囲" setInput={()=>{}} field={{current:null}} composing={{current:false}} />);
}
test('目標達成後も最後の回答詳細と結果ボタンを表示する', () => {
  const html = render('completed');
  expect(html).toContain('優位'); expect(html).toContain('周囲');
  expect(html).toContain('高・低・低'); expect(html).toContain('正解！');
  expect(html).toContain('結果を見る'); expect(html).not.toContain('次のお題へ');
  expect(html).not.toContain('スキップ'); expect(html).toContain('0.5 秒');
  expect(html).toMatch(/type="button">結果を見る<\/button>/);
});
test('途中の正解では次のお題へ進める', () => {
  const html = render(null);
  expect(html).toContain('次のお題へ'); expect(html).toContain('リタイアして結果を見る');
  expect(html).toMatch(/type="button">次のお題へ<\/button>/);
  expect(html).toMatch(/type="button"[^>]*>リタイアして結果を見る<\/button>/);
});
