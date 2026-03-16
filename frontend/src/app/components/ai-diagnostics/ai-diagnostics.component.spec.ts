import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AiDiagnosticsComponent } from './ai-diagnostics.component';

describe('AiDiagnosticsComponent', () => {
  let component: AiDiagnosticsComponent;
  let fixture: ComponentFixture<AiDiagnosticsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AiDiagnosticsComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(AiDiagnosticsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
