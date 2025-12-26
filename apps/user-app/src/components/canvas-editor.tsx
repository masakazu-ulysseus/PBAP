"use client";

import { useRef, useCallback } from "react";
import { Stage, Layer, Line, Image as KonvaImage } from "react-konva";
import type { KonvaEventObject } from "konva/lib/Node";

interface CanvasLine {
  points: number[];
  stroke: string;
  strokeWidth: number;
}

interface CanvasEditorProps {
  image: HTMLImageElement;
  width: number;
  height: number;
  lines: CanvasLine[];
  onLinesChange: (lines: CanvasLine[]) => void;
  strokeColor: string;
  strokeWidth: number;
}

export function CanvasEditor({
  image,
  width,
  height,
  lines,
  onLinesChange,
  strokeColor,
  strokeWidth,
}: CanvasEditorProps) {
  const isDrawing = useRef(false);

  // 画像のスケール計算（元画像サイズ → 表示サイズ）
  const scaleX = width / image.width;
  const scaleY = height / image.height;

  const handleMouseDown = useCallback(
    (e: KonvaEventObject<MouseEvent | TouchEvent>) => {
      isDrawing.current = true;
      const pos = e.target.getStage().getPointerPosition();
      onLinesChange([
        ...lines,
        {
          points: [pos.x, pos.y],
          stroke: strokeColor,
          strokeWidth: strokeWidth,
        },
      ]);
    },
    [lines, onLinesChange, strokeColor, strokeWidth]
  );

  const handleMouseMove = useCallback(
    (e: KonvaEventObject<MouseEvent | TouchEvent>) => {
      if (!isDrawing.current) return;
      const stage = e.target.getStage();
      const point = stage.getPointerPosition();
      const lastLine = lines[lines.length - 1];
      if (!lastLine) return;

      const newLines = [
        ...lines.slice(0, -1),
        {
          ...lastLine,
          points: [...lastLine.points, point.x, point.y],
        },
      ];
      onLinesChange(newLines);
    },
    [lines, onLinesChange]
  );

  const handleMouseUp = useCallback(() => {
    isDrawing.current = false;
  }, []);

  return (
    <Stage
      width={width}
      height={height}
      onMouseDown={handleMouseDown}
      onMousemove={handleMouseMove}
      onMouseup={handleMouseUp}
      onTouchStart={handleMouseDown}
      onTouchMove={handleMouseMove}
      onTouchEnd={handleMouseUp}
    >
      <Layer>
        <KonvaImage image={image} scaleX={scaleX} scaleY={scaleY} />
        {lines.map((line, i) => (
          <Line
            key={i}
            points={line.points}
            stroke={line.stroke}
            strokeWidth={line.strokeWidth}
            tension={0.5}
            lineCap="round"
            lineJoin="round"
          />
        ))}
      </Layer>
    </Stage>
  );
}
