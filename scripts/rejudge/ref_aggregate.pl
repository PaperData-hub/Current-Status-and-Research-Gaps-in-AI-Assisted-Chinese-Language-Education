#!/usr/bin/perl
# ref_aggregate.pl — 논문별 참고문헌 분류 집계(원고 <표 12>의 공개용 입력). KCI 원자료가 필요하다.
#
# 참고문헌 목록(KCI 원자료)은 재배포하지 않으므로, 논문마다 건수만 남긴다.
# <표 12>는 이 집계로 scripts/analysis/references_school.py가 계산한다.
#   - 대상: 확정 코퍼스(include=Y) 가운데 KCI가 참고문헌 목록을 준 논문(ref_available, 목록 비어 있지 않음)
#   - 국내: 제목·학술지명·저자에 한글이 있는 문헌 / 중문: 한글 없이 한자가 있는 문헌 / 그 밖: 나머지 국제 문헌
#   - 분야: 학술지명으로만 가른다(교육 → 문학 → 언어학 → 기타 순). 학술지명이 없으면 분야 분모에서 뺀다.
#
# 사용: perl scripts/rejudge/ref_aggregate.pl [--date 1161_20261001]
# 입력: data/rejudge/merged_<DATE>.json(판정), data/corpus_full_merged.json(KCI 상세 응답 병합본)
# 산출: analysis/ref_aggregate_<DATE>.csv(UTF-8, BOM), 표준 출력에 언어군별 합계
use strict; use warnings; use utf8;
use feature 'unicode_strings';
no warnings 'surrogate';
binmode STDOUT, ':encoding(UTF-8)';

my $DATE = '1161_20261001';
for my $i (0 .. $#ARGV) { $DATE = $ARGV[$i + 1] if $ARGV[$i] eq '--date' }
(my $REPO = $0) =~ s{[\\/]scripts[\\/]rejudge[\\/][^\\/]+$}{};
$REPO = '.' if $REPO eq $0;

sub slurp { my $f = shift; open my $h, '<:encoding(UTF-8)', $f or die "$f: $!"; local $/; my $t = <$h>; close $h; $t }

my %MAP = ('"' => '"', '\\' => '\\', '/' => '/', b => "\b", f => "\f", n => "\n", r => "\r", t => "\t");
sub junesc {
  my $s = shift;
  return '' if !defined $s || $s eq 'null';
  $s =~ s/^"//; $s =~ s/"$//;
  $s =~ s/\\(?:u([0-9a-fA-F]{4})|(["\\\/bfnrt]))/defined $1 ? chr(hex $1) : $MAP{$2}/ge;
  $s =~ s/([\x{D800}-\x{DBFF}])([\x{DC00}-\x{DFFF}])/chr(0x10000 + ((ord($1) - 0xD800) << 10) + (ord($2) - 0xDC00))/ge;
  return $s;
}

# ── 확정 판정: 포함 여부와 언어군 ─────────────────────────────────────────
my $mj = slurp("$REPO/data/rejudge/merged_$DATE.json");
my (%group, @order);
while ($mj =~ /\{"arti_id": "(ART\d+)"(.*?)(?=\{"arti_id": "ART|\]\s*\z)/gs) {
  my ($id, $r) = ($1, $2);
  next unless $r =~ /"include": "Y"/;
  my ($g) = $r =~ /"group": "([^"]*)"/;
  $group{$id} = $g; push @order, $id;
}
undef $mj;

# ── 원고 <표 12>의 분류 규칙(학술지명 정규식) ───────────
my $EDU = qr/교육|교수|학습|교과|교사|수업|리터러시|작문연구|독서연구|educat|learn|teach|pedagog|instruct|curricul|tesol|\bcall\b|recall|computer assisted|language learning|language teaching|second language writing|assessing writing|system$|elt journal|tesl|efl|esl|literacy|school/i;
my $LIT = qr/문학|소설|시학|시가|고전|비평|문예|literat|literary|poetry|poetic|文學|文学|詩|诗/i;
my $LING = qr/언어|어학|국어학|문법|음성|의미|형태|통사|화용|담화|어문|말뭉치|코퍼스|번역|통역|우리말|배달말|한글|국어|영어학|중국어|linguist|language|grammar|phonet|phonolog|semantic|syntax|pragmat|discourse|corpus|translat|interpret|語言|语言|語法|语法|漢語|汉语|中國語|中国语/i;
my $HANGUL = qr/[\x{AC00}-\x{D7A3}]/;
my $HANJA  = qr/[\x{4E00}-\x{9FFF}]/;

sub field {
  my $j = shift; $j =~ s/^\s+//; $j =~ s/\s+$//;
  return '' if $j eq '';
  return '교육' if $j =~ $EDU;
  return '문학' if $j =~ $LIT;
  return '언어학' if $j =~ $LING;
  return '기타';
}

# ── KCI 상세 응답에서 참고문헌 목록 읽기 ──────────────────────────────────
my $STR = qr/"(?:[^"\\]|\\.)*"/s;
my $VAL = qr/(?:$STR|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|null|true|false)/;
my $OBJ = qr/\{(?:$STR:$VAL(?:,$STR:$VAL)*)?\}/;

my $raw = slurp("$REPO/data/corpus_full_merged.json");
my %agg;
while ($raw =~ /\{"arti_id":"(ART\d+)"/g) {
  my $id = $1; my $pos = pos($raw);
  next unless exists $group{$id};
  my $end = index($raw, '{"arti_id":"ART', $pos); $end = length($raw) if $end < 0;
  my $rec = substr($raw, $pos, $end - $pos);
  my ($avail) = $rec =~ /"ref_available":(true|false)/;
  my @refs;
  if ($rec =~ /"references":\[/g) {
    while (1) {
      if ($rec =~ /\G\]/gc) { last }
      $rec =~ /\G($OBJ),?/gc or die "$id: 참고문헌 목록을 읽지 못함\n";
      my $o = $1;
      my %f;
      for my $k (qw(title author journal)) { ($f{$k}) = $o =~ /"$k":($STR|null)/; $f{$k} = junesc($f{$k}) }
      push @refs, \%f;
    }
  }
  my %a = (avail => ($avail && $avail eq 'true') ? 1 : 0, n => 0, ko => 0, zh => 0, en => 0, nj => 0, edu => 0, ling => 0, lit => 0, oth => 0);
  if ($a{avail} && @refs) {
    for my $f (@refs) {
      my $s = join(' ', $f->{title}, $f->{journal}, $f->{author});
      $a{n}++;
      if ($s =~ $HANGUL) { $a{ko}++ } elsif ($s =~ $HANJA) { $a{zh}++ } else { $a{en}++ }
      my $fd = field($f->{journal});
      next if $fd eq '';
      $a{nj}++;
      $a{ {'교육' => 'edu', '언어학' => 'ling', '문학' => 'lit', '기타' => 'oth'}->{$fd} }++;
    }
  } else { $a{avail} = 0 }
  $agg{$id} = \%a;
}
undef $raw;
my @missing = grep { !exists $agg{$_} } @order;
die "원자료에 없는 확정 논문 " . scalar(@missing) . "편\n" if @missing;

# ── 산출 ────────────────────────────────────────────────────────────────
my $out = "$REPO/analysis/ref_aggregate_$DATE.csv";
open my $o, '>:encoding(UTF-8)', $out or die "$out: $!";
print $o "\x{FEFF}artiId,언어군,참고문헌목록,참고문헌수,국내_한글,중문_한자,그밖_국제,학술지명있음,교육,언어학,문학,기타\n";
for my $id (sort @order) {
  my $a = $agg{$id};
  print $o join(',', $id, $group{$id}, $a->{avail} ? 'Y' : 'N', @{$a}{qw(n ko zh en nj edu ling lit oth)}), "\n";
}
close $o;

printf "확정 코퍼스 %d편 → %s\n", scalar(@order), $out;
for my $g ('영어', '한국어', '중국어') {
  my @ids = grep { $group{$_} eq $g } @order;
  my @w = grep { $agg{$_}{avail} } @ids;
  my %s; for my $id (@w) { $s{$_} += $agg{$id}{$_} for qw(n ko zh en nj edu ling lit oth) }
  printf "%s: 참고문헌 목록 %d/%d편, 편당 %.1f건, 국내 %.1f%%, 국제 %.1f%%(중문 %.1f%%), 학술지명 있음 %d건(%.0f%%), 교육 %.1f%%, 언어학 %.1f%%, 문학 %.1f%%, 기타 %.1f%%\n",
    $g, scalar(@w), scalar(@ids), $s{n} / @w, 100 * $s{ko} / $s{n}, 100 * ($s{zh} + $s{en}) / $s{n}, 100 * $s{zh} / $s{n},
    $s{nj}, 100 * $s{nj} / $s{n}, 100 * $s{edu} / $s{nj}, 100 * $s{ling} / $s{nj}, 100 * $s{lit} / $s{nj}, 100 * $s{oth} / $s{nj};
}
