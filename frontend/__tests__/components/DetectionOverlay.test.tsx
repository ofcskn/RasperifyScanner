import { computeImageRect } from '../../components/DetectionOverlay';

describe('computeImageRect (bbox overlay scaling)', () => {
  it('fills width and letterboxes top/bottom when frame is wider than container', () => {
    // 16:9 frame in a square-ish container -> full width, vertical letterbox.
    const r = computeImageRect(320, 320, 1280, 720);
    expect(r.dispW).toBeCloseTo(320);
    expect(r.dispH).toBeCloseTo(180); // 320 / (1280/720)
    expect(r.offX).toBeCloseTo(0);
    expect(r.offY).toBeCloseTo(70); // (320 - 180) / 2
  });

  it('fills height and letterboxes left/right when frame is taller than container', () => {
    // 9:16 frame in a wide container -> full height, horizontal letterbox.
    const r = computeImageRect(400, 200, 720, 1280);
    expect(r.dispH).toBeCloseTo(200);
    expect(r.dispW).toBeCloseTo(112.5); // 200 * (720/1280)
    expect(r.offY).toBeCloseTo(0);
    expect(r.offX).toBeCloseTo(143.75);
  });

  it('maps a normalized box into the displayed image rect', () => {
    const { offX, offY, dispW, dispH } = computeImageRect(320, 320, 1280, 720);
    const [x1, y1, x2, y2] = [0.5, 0.5, 1.0, 1.0];
    const left = offX + x1 * dispW;
    const top = offY + y1 * dispH;
    expect(left).toBeCloseTo(160); // centered horizontally
    expect(top).toBeCloseTo(70 + 90); // letterbox offset + half of 180
    expect((x2 - x1) * dispW).toBeCloseTo(160);
  });

  it('is safe when sizes are zero (not yet laid out)', () => {
    const r = computeImageRect(0, 0, 1280, 720);
    expect(r.dispW).toBe(0);
    expect(r.dispH).toBe(0);
  });
});
