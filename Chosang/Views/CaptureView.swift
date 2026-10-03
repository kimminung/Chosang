//
//  CaptureView.swift
//  초상 (iOS)
//
//  캡처 탭 진입점: TrueDepth 가 있으면 ARKit `FaceCaptureSession`, 없으면(시뮬레이터·구형 기기) 사진 폴백 `PhotoCaptureSession` —
//  둘 다 같은 iPhone 가이드 화면 `GuidedCaptureView` 를 쓴다. 번들 포맷도 같다(폴백은 `sparse = true`).
//

#if os(iOS)
import SwiftUI
import ChosangCapture

struct CaptureView: View {
    var body: some View {
        if FaceCaptureSession.isSupported {
            GuidedCaptureView(source: FaceCaptureSession())
        } else {
            GuidedCaptureView(source: PhotoCaptureSession())
        }
    }
}
#endif
