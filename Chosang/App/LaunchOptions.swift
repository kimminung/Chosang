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

    static var current: LaunchOptions {
        var o = LaunchOptions()
        for arg in CommandLine.arguments.dropFirst() {
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
            default: break
            }
        }
        return o
    }
}
