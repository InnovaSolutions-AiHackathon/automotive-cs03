import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MaintenanceTimelineComponent } from './maintenance-timeline.component';

describe('MaintenanceTimelineComponent', () => {
  let component: MaintenanceTimelineComponent;
  let fixture: ComponentFixture<MaintenanceTimelineComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [MaintenanceTimelineComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(MaintenanceTimelineComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
