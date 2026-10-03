import Testing
import Foundation
@testable import ChosangCore
@testable import ChosangCapture

/// T-202 가이드 상태 기계.
@Suite("캡처 가이드 (T-202)")
struct CaptureGuideTests {
    @Test("게이트를 0.7 s 유지하면 한 번만 촬영 신호, 흔들리면 타이머 리셋")
    func holdTimer() {
        var g = CaptureGuide(holdSeconds: 0.7)
        // #expect 매크로 안에서는 mutating 호출을 못 하므로 결과를 먼저 받는다
        func tick(_ ok: Bool, _ t: Double) -> Bool { g.update(gateOK: ok, now: t) }
        #expect(g.current == .front)
        let a = tick(true, 10.0); #expect(!a)
        let b = tick(true, 10.5); #expect(!b)
        #expect(abs(g.holdProgress - 0.5 / 0.7) < 1e-9)
        let c = tick(false, 10.6); #expect(!c)             // 흔들림 → 리셋
        #expect(g.holdProgress == 0)
        let d = tick(true, 11.0); #expect(!d)
        let e = tick(true, 11.7); #expect(e)               // 0.7 s 유지 → 촬영
        #expect(g.holdProgress == 0)
        let f = tick(true, 11.75); #expect(!f)             // 리셋 후 다시 시작
    }

    @Test("촬영 → 다음 스텝, 건너뛰기, 재촬영, 완료")
    func flow() {
        var g = CaptureGuide()
        g.markCaptured(.front)
        #expect(g.current == .left && g.state(of: .front) == .captured && g.completedCount == 1)
        g.skip()                                           // 왼쪽 건너뜀
        #expect(g.current == .right && g.state(of: .left) == .skipped)
        g.markCaptured(.right); g.markCaptured(.up); g.markCaptured(.smile)
        #expect(g.isComplete && g.current == nil)
        let fired = g.update(gateOK: true, now: 1)
        #expect(!fired)                                    // 완료 상태에서는 신호 없음
        g.retake(.left)                                    // 건너뛴 컷으로 돌아감
        #expect(g.current == .left && !g.isComplete && g.state(of: .left) == .current)
        g.markCaptured(.left)
        #expect(g.isComplete && g.completedCount == 5)
        g.retake(.front)
        #expect(g.current == .front && g.completedCount == 4)
        g.reset()
        #expect(g.current == .front && g.completedCount == 0 && g.state(of: .left) == .pending)
    }

    @Test("중간 컷을 다시 찍으면 이후 미촬영 컷으로 이어진다")
    func retakeThenContinue() {
        var g = CaptureGuide()
        g.markCaptured(.front); g.markCaptured(.left)
        g.retake(.front)
        g.markCaptured(.front)
        #expect(g.current == .right)                       // left 는 이미 있음 → right 로
    }
}
