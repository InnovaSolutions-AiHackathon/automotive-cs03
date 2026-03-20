import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { ApiService } from '../../services/api.service';
import { VehicleDetailComponent } from '../vehicle-detail/vehicle-detail.component';

export interface VehicleItem {
  vehicle_code: string;
  make: string;
  model: string;
  year: number;
  vin?: string;
  odometer?: number;
  fuel_level?: number;
  battery_voltage?: number;
  engine_temp?: number;
  oil_life?: number;
  active_dtcs?: string[];
  status?: 'ok' | 'warning' | 'critical';
}

@Component({
  selector: 'app-vehicles-info',
  templateUrl: './vehicles-info.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, VehicleDetailComponent],
  styleUrls: ['./vehicles-info.component.scss']
})
export class VehiclesinfoComponent implements OnInit, OnDestroy {
  vehicles: VehicleItem[] = [];
  selectedVehicle: VehicleItem | null = null;
  loading = true;
  error = '';

  private _sub?: Subscription;

  constructor(
    private api: ApiService,
    private cd: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this._load();
  }

  ngOnDestroy(): void {
    this._sub?.unsubscribe();
  }

  selectVehicle(v: VehicleItem): void {
    this.selectedVehicle = v;
    this.cd.markForCheck();
  }

  private _load(): void {
    this.loading = true;
    this.error = '';
    this.vehicles = [];
    this.cd.markForCheck();

    this._sub = this.api.listVehicles().subscribe({
      next: (list) => {
        this.vehicles = list.map(v => ({
          ...v,
          status: this._deriveStatus(v),
        }));
        this.loading = false;
        this.cd.markForCheck();
      },
      error: () => {
        this.error = 'Failed to load vehicles. Please try again.';
        this.loading = false;
        this.cd.markForCheck();
      }
    });
  }

  private _deriveStatus(v: any): 'ok' | 'warning' | 'critical' {
    if (v.active_dtcs?.length > 1) return 'critical';
    if (v.active_dtcs?.length === 1) return 'warning';
    if (v.fuel_level < 15 || v.oil_life < 10) return 'critical';
    if (v.fuel_level < 25 || v.oil_life < 20) return 'warning';
    return 'ok';
  }
}
