//
//  CaptureGuide.swift
//  ChosangCapture
//
//  5컷 가이드 상태 기계 (T-202 의 1차, 전 플랫폼 순수 로직): 현재 스텝 · 게이트 유지 타이머(0.7 s) → 자동 촬영 신호 · 건너뛰기 · 재촬영.
//  UI(iPhone `GuidedCaptureView`)와 캡처 소스(ARKit `FaceCaptureSession` / 사진 폴백 `PhotoCaptureSession`)에서 독립이라 테스트가 지킨다.
//

import Foundation
import ChosangCore

public struct CaptureGuide: Sendable, Equatable {
    public var steps: [ShotKind]
    public var holdSeconds: Double
    public private(set) var currentIndex: Int?
    public private(set) var captured: Set<ShotKind> = []
    public private(set) var skipped: Set<ShotKind> = []
    public private(set) var holdStart: Double?
    /// 게이트 유지 진행률 0…1 (UI 링)
    public private(set) var holdProgress: Double = 0

    public init(steps: [ShotKind] = ShotKind.allCases, holdSeconds: Double = 0.7) {
        self.steps = steps
        self.holdSeconds = holdSeconds
        currentIndex = steps.isEmpty ? nil : 0
    }

    public var current: ShotKind? { currentIndex.map { steps[$0] } }
    public var isComplete: Bool { currentIndex == nil }
    public var completedCount: Int { captured.count }
    public var totalCount: Int { steps.count }

    public enum StepState: Sendable, Equatable { case pending, current, captured, skipped }
    public func state(of kind: ShotKind) -> StepState {
        if captured.contains(kind) { return .captured }
        if skipped.contains(kind) { return .skipped }
        if current == kind { return .current }
        return .pending
    }

    /// 매 틱: 게이트 통과 여부와 현재 시각(초). 유지 시간이 차면 true(지금 촬영하라)를 돌려주고 타이머를 리셋한다.
    public mutating func update(gateOK: Bool, now: Double) -> Bool {
        guard !isComplete else { holdStart = nil; holdProgress = 0; return false }
        guard gateOK else { holdStart = nil; holdProgress = 0; return false }
        if holdStart == nil { holdStart = now }
        let elapsed = now - (holdStart ?? now)
        holdProgress = holdSeconds > 0 ? min(1, elapsed / holdSeconds) : 1
        if elapsed + 0.001 >= holdSeconds {   // 1 ms 허용 (부동소수 합산 오차)
            holdStart = nil
            holdProgress = 0
            return true
        }
        return false
    }

    /// 촬영 완료 → 다음 미촬영 스텝으로.
    public mutating func markCaptured(_ kind: ShotKind) {
        captured.insert(kind)
        skipped.remove(kind)
        holdStart = nil; holdProgress = 0
        advance()
    }

    /// 현재 스텝 건너뛰기 (미소 컷 등). 이미 촬영된 건 유지.
    public mutating func skip() {
        guard let k = current else { return }
        skipped.insert(k)
        holdStart = nil; holdProgress = 0
        advance()
    }

    /// 해당 스텝으로 돌아가 다시 찍는다.
    public mutating func retake(_ kind: ShotKind) {
        guard let i = steps.firstIndex(of: kind) else { return }
        captured.remove(kind)
        skipped.remove(kind)
        currentIndex = i
        holdStart = nil; holdProgress = 0
    }

    public mutating func reset() {
        captured.removeAll(); skipped.removeAll()
        currentIndex = steps.isEmpty ? nil : 0
        holdStart = nil; holdProgress = 0
    }

    /// 다음 스텝: 현재 이후에서 미처리(촬영·건너뜀 아님) 스텝, 없으면 앞에서부터, 그래도 없으면 완료.
    private mutating func advance() {
        let start = (currentIndex ?? -1) + 1
        let order = Array(steps.indices.dropFirst(start)) + Array(steps.indices.prefix(start))
        currentIndex = order.first { !captured.contains(steps[$0]) && !skipped.contains(steps[$0]) }
    }
}
