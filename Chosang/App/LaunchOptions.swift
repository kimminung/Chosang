//
//  LaunchOptions.swift
//  초상
//
//  시뮬레이터 자동 실행 인자 (CLAUDE.md): `fixture=<name> clip=<name> tab=<name> template=<default|synthetic|legacy> report=1 sheet=1 previz=1`.
//  예) Xcode 스킴 Arguments: template=default clip=bow tab=preview
//

import Foundation

struct LaunchOptions: Sendable {
    var fixture: String?
    var clip: String?
    var tab: String?
    var template: String?
    /// `report=1`: 10 초 뒤 Documents/chosang-report.txt 에 수치 기록 (DEBUG 자동화)
    var report = false
    /// `sheet=1`: 셰이프 시트 모드(52 셰이프 순환, 턴테이블 끔, 프리비즈 카메라)
    var sheet = false
    /// `previz=1`: 프리비즈 카메라 고정
    var previz = false
    /// `usdz=0`: 기본 템플릿의 Template.usdz 오버레이(눈알·입안) 생략 (진단용)
    var usdzOverlay = true
    /// `camera=1`: 사진 폴백 캡처 탭(Mac·iOS 폴백)이 뜨자마자 카메라를 시작 (스크린샷 자동화)
    var camera = false

    /// 명령행 인자 + 환경변수 `CHOSANG_ARGS="tab=capture camera=1"`.
    /// macOS 는 대시 없는 명령행 인자를 "열 문서" 로 취급해(문서 타입 선언 앱) 기본 창을 만들지 않으므로,
    /// `open Chosang.app --env CHOSANG_ARGS="…"` 로 띄울 때는 환경변수를 쓴다. Xcode 스킴 Arguments 는 그대로 동작한다.
    static var current: LaunchOptions {
        var o = LaunchOptions()
        let env = (ProcessInfo.processInfo.environment["CHOSANG_ARGS"] ?? "").split(separator: " ").map(String.init)
        for arg in CommandLine.arguments.dropFirst() + env {
            let parts = arg.split(separator: "=", maxSplits: 1).map(String.init)
            guard parts.count == 2 else { continue }
            let on = parts[1] == "1" || parts[1] == "true"
            switch parts[0] {
            case "fixture": o.fixture = parts[1]
            case "clip": o.clip = parts[1]
            case "tab": o.tab = parts[1]
            case "template": o.template = parts[1]
            case "report": o.report = on
            case "sheet": o.sheet = on
            case "previz": o.previz = on
            case "usdz": o.usdzOverlay = on
            case "camera": o.camera = on
            default: break
            }
        }
        return o
    }
}
