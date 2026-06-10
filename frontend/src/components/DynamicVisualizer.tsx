import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

export const DynamicVisualizer = ({ config, fallbackTitle }: { config: any, fallbackTitle?: string }) => {
  // If config is string, try to parse
  let parsed = config;
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed);
    } catch (e) {
      return <div>데이터 파싱 오류</div>;
    }
  }

  // AI가 JSON 배열만 반환했을 경우 방어 로직 (이전 버전 호환성)
  if (Array.isArray(parsed)) {
    parsed = {
      type: 'table',
      columns: Array.from(new Set(parsed.flatMap(Object.keys))).map(key => ({ key, label: key })),
      data: parsed
    };
  }

  if (!parsed || typeof parsed !== 'object') {
    return <div>유효하지 않은 시각화 데이터입니다.</div>;
  }

  if (
    (parsed.chartType === 'line' || parsed.type === 'chart' || parsed.kind === 'graph') &&
    Array.isArray(parsed.series) &&
    parsed.series.length === 1 &&
    Array.isArray(parsed.data) &&
    parsed.data.length > 0
  ) {
    const sourceXKey = parsed.xAxisKey || 'name';
    const sourceSeries = parsed.series[0];
    const sourceValueKey = sourceSeries?.dataKey;
    const rowMap = new Map<string, any>();
    const yearKeys: string[] = [];

    parsed.data.forEach((row: any) => {
      const label = String(row?.[sourceXKey] ?? '');
      const match = label.match(/^(\d{4})(?:년)?[-.\/\s]*(\d{1,2})월?$/);
      if (!match || !sourceValueKey) return;

      const yearKey = `${match[1]}년`;
      const monthLabel = `${Number(match[2])}월`;
      if (!yearKeys.includes(yearKey)) yearKeys.push(yearKey);

      const current = rowMap.get(monthLabel) || { month: monthLabel, monthOrder: Number(match[2]) };
      const numericValue = Number(row?.[sourceValueKey]);
      current[yearKey] = Number.isFinite(numericValue) ? numericValue : null;
      rowMap.set(monthLabel, current);
    });

    if (rowMap.size > 0 && yearKeys.length > 1) {
      parsed = {
        ...parsed,
        chartType: 'line',
        xAxisKey: 'month',
        data: Array.from(rowMap.values()).sort((a, b) => a.monthOrder - b.monthOrder),
        series: yearKeys.map((yearKey, index) => ({
          dataKey: yearKey,
          name: yearKey,
          color: ['#94a3b8', '#64748b', '#0f172a', '#0ea5a4', '#2563eb', '#f59e0b'][index % 6],
          yAxisId: 'left',
        })),
      };
    }
  }

  const { type, chartType, xAxisKey, columns, series, data, rows, kind, items } = parsed;
  const layout = parsed.layout || {};
  
  // 구버전(rows, kind) 호환성 유지
  const safeData = Array.isArray(data) && data.length > 0 ? data : (Array.isArray(rows) ? rows : []);
  const actualType = (chartType || (Array.isArray(series) && series.length > 0))
    ? 'chart'
    : type || (kind === 'graph' ? 'chart' : kind) || 'table';

  const renderImageExtraction = () => {
    const imageItems = Array.isArray(items) ? items : [];
    if (imageItems.length === 0) {
      return (
        <div style={{ padding: 18, border: '1px solid #cbd5e1', borderRadius: 8, color: '#475569', background: '#f8fafc' }}>
          추출 가능한 이미지 파일을 찾지 못했습니다.
        </div>
      );
    }

    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        {imageItems.map((item: any, index: number) => (
          <article
            key={item.id || `${item.source}-${index}`}
            style={{
              border: '1px solid #cbd5e1',
              borderRadius: 8,
              background: '#ffffff',
              overflow: 'hidden',
              minWidth: 0,
            }}
          >
            {item.dataUrl ? (
              <div style={{ background: '#f8fafc', aspectRatio: '4 / 3', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <img
                  src={item.dataUrl}
                  alt={item.name || item.source || '추출 이미지'}
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                />
              </div>
            ) : (
              <div style={{ background: '#f8fafc', minHeight: 132, padding: 14, color: '#334155', fontSize: 13, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                {item.previewText || item.ocrText || '이미지 미리보기를 표시할 수 없습니다.'}
              </div>
            )}
            <div style={{ padding: 12, display: 'grid', gap: 8 }}>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                <strong style={{ color: '#0f172a', fontSize: 14 }}>{item.source || item.name || `추출 항목 ${index + 1}`}</strong>
                <span style={{ border: '1px solid #99f6e4', background: '#ecfeff', color: '#0f766e', borderRadius: 999, padding: '2px 7px', fontSize: 11, fontWeight: 800 }}>
                  {item.kind || 'image'}
                </span>
              </div>
              {(item.width && item.height) && (
                <span style={{ color: '#64748b', fontSize: 12 }}>{item.width}x{item.height}px</span>
              )}
              {(item.ocrText || item.previewText) && (
                <p style={{ margin: 0, color: '#475569', fontSize: 12, lineHeight: 1.45, maxHeight: 72, overflow: 'auto' }}>
                  {item.ocrText || item.previewText}
                </p>
              )}
              {item.dataUrl && (
                <a
                  href={item.dataUrl}
                  download={item.name || `extracted-image-${index + 1}.png`}
                  style={{
                    justifySelf: 'start',
                    border: '1px solid #0f766e',
                    color: '#0f766e',
                    borderRadius: 6,
                    padding: '6px 9px',
                    textDecoration: 'none',
                    fontSize: 12,
                    fontWeight: 800,
                  }}
                >
                  추출 파일 저장
                </a>
              )}
            </div>
          </article>
        ))}
      </div>
    );
  };

  const renderTable = () => {
    const cols = Array.isArray(columns) && columns.length > 0 
      ? columns 
      : Array.from(new Set(safeData.flatMap(Object.keys))).map(key => ({ key, label: key }));

    // AI가 지정한 테마(theme)가 있으면 적용, 없으면 기본값
    const theme = parsed.theme || {};
    const headerBg = theme.headerBackground || '#f1f5f9';
    const headerColor = theme.headerTextColor || '#0f172a';
    const cellBg = theme.cellBackground || '#ffffff';
    const cellColor = theme.cellTextColor || '#334155';
    const borderColor = theme.borderColor || '#cbd5e1';

    return (
      <div style={{ width: '100%', height: '100%', overflowX: 'auto', overflowY: 'auto' }}>
        <table
          className="dynamic-table"
          style={{
            width: '100%',
            borderCollapse: 'separate',
            borderSpacing: 0,
            border: `1px solid ${borderColor}`,
            borderRadius: 8,
            overflow: 'hidden',
            tableLayout: 'auto',
          }}
        >
          <thead>
            <tr>
              {cols.map((col: any, i: number) => (
                <th
                  key={`th-${i}`}
                  style={{
                    background: headerBg,
                    color: headerColor,
                    borderBottom: `1px solid ${borderColor}`,
                    borderRight: i < cols.length - 1 ? `1px solid ${borderColor}` : 'none',
                    padding: '10px 12px',
                    textAlign: 'left',
                    fontSize: 13,
                    fontWeight: 800,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {col.label || col.key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {safeData.map((row: any, rIndex: number) => (
              <tr key={`tr-${rIndex}`}>
                {cols.map((col: any, cIndex: number) => (
                  <td
                    key={`td-${rIndex}-${cIndex}`}
                    style={{
                      background: cellBg,
                      color: cellColor,
                      borderBottom: rIndex < safeData.length - 1 ? `1px solid ${borderColor}` : 'none',
                      borderRight: cIndex < cols.length - 1 ? `1px solid ${borderColor}` : 'none',
                      padding: '10px 12px',
                      fontSize: 13,
                      fontWeight: 650,
                      verticalAlign: 'top',
                    }}
                  >
                    {row[col.key] !== undefined && row[col.key] !== null ? String(row[col.key]) : '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderChart = () => {
    if (!series || !Array.isArray(series) || series.length === 0) {
      return <div>차트 설정(Series)이 누락되었습니다.</div>;
    }

    const xKey = xAxisKey || 'name';
    const numericValues = safeData.flatMap((row: any) =>
      series
        .filter((s: any) => (s.yAxisId || 'left') === 'left')
        .map((s: any) => Number(row?.[s.dataKey]))
        .filter((value: number) => Number.isFinite(value))
    );
    const minValue = numericValues.length ? Math.min(...numericValues) : 0;
    const maxValue = numericValues.length ? Math.max(...numericValues) : 0;
    const valueRange = maxValue - minValue;
    const looksLikeYear = minValue >= 1800 && maxValue <= 2300 && valueRange > 0;
    const yPadding = Math.max(2, Math.ceil(valueRange * 0.15));
    const leftYAxisDomain: any = looksLikeYear ? [minValue - yPadding, maxValue + yPadding] : ['auto', 'auto'];
    const yTickFormatter = (value: any) => looksLikeYear ? String(Math.round(Number(value))) : String(value);

    if (chartType === 'pie') {
      const pieData = safeData;
      const pieColor = series[0]?.color || '#0ea5a4';
      const COLORS = [pieColor, '#f59e0b', '#3b82f6', '#ef4444', '#10b981', '#8b5cf6'];
      return (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              dataKey={series[0].dataKey}
              nameKey={xKey}
              cx="50%"
              cy="50%"
              outerRadius={100}
              fill={pieColor}
              label
            >
              {pieData.map((entry: any, index: number) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      );
    }

    const hasRightAxis = series.some((s: any) => s.yAxisId === 'right');

    if (chartType === 'line') {
      return (
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={safeData} margin={{ top: 22, right: hasRightAxis ? 16 : 34, left: 12, bottom: 34 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="left" orientation="left" domain={leftYAxisDomain} tickFormatter={yTickFormatter} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} width={48} />
            {hasRightAxis && (
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            )}
            <Tooltip
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}
            />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            {series.map((s: any, idx: number) => (
              <Line
                key={idx}
                yAxisId={s.yAxisId || 'left'}
                type="monotone"
                dataKey={s.dataKey}
                name={s.name || s.dataKey}
                stroke={s.color || '#0ea5a4'}
                strokeWidth={2.5}
                dot={{ r: 5, strokeWidth: 2, fill: '#ffffff' }}
                activeDot={{ r: 7 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      );
    }

    // Default to Bar chart
    return (
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={safeData} margin={{ top: 22, right: hasRightAxis ? 16 : 34, left: 12, bottom: 34 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
          <YAxis yAxisId="left" orientation="left" domain={leftYAxisDomain} tickFormatter={yTickFormatter} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} width={48} />
          {hasRightAxis && (
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
          )}
          <Tooltip
            cursor={{ fill: '#f1f5f9' }}
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          {series.map((s: any, idx: number) => (
            <Bar
              key={idx}
              yAxisId={s.yAxisId || 'left'}
              dataKey={s.dataKey}
              name={s.name || s.dataKey}
              fill={s.color || '#0ea5a4'}
              radius={[4, 4, 0, 0]}
              maxBarSize={50}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div
      className="dynamic-visualizer"
      style={{
        width: '100%',
        padding: '16px 0 24px 0',
        minHeight: layout.aspectRatio ? 'auto' : '340px',
        aspectRatio: layout.aspectRatio,
      }}
    >
      {actualType === 'image' && renderImageExtraction()}
      {actualType === 'chart' && renderChart()}
      {actualType === 'table' && renderTable()}
      {!['chart', 'table', 'image'].includes(actualType) && renderTable()}
    </div>
  );
};
