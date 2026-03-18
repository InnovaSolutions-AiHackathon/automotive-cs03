import { ChangeDetectorRef, Component, Input, NgZone, OnInit, SimpleChanges } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-vehicle-detail',
  standalone: true,
  imports: [CommonModule, DecimalPipe],
  templateUrl: './vehicle-detail.component.html',
  styleUrls: ['./vehicle-detail.component.scss']

})
export class VehicleDetailComponent implements OnInit {
  @Input() vehicleCode!: string;
  @Input() repairType = 'engine';

  result: any = null;
  vehicle: any = null;
  loading = true;

  stats: { icon: string; label: string; value: string; alert: boolean }[] = [];

  constructor(private api: ApiService, private ngZone: NgZone, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.loadVehicle();
    this.loadWarranty();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['vehicleCode']) {
      this.loadVehicle();
      this.loadWarranty();
    }
  }

  private loadVehicle() {
    this.loading = true;
    this.vehicle = null; // reset before new call

    this.api.getVehicle(this.vehicleCode).subscribe({
      next: (v) => {
        if (v && !v.detail) {
          // valid vehicle object
          this.vehicle = v;
          this.stats = [
            { icon: '⛽', label: 'Fuel',    value: `${v.fuel_level}%`, alert: v.fuel_level < 20 },
            { icon: '🔋', label: 'Battery', value: `${v.battery_voltage}V`, alert: v.battery_voltage < 12.0 },
            { icon: '🌡️', label: 'Engine',  value: `${v.engine_temp}°C`, alert: v.engine_temp > 105 },
            { icon: '🛢️', label: 'Oil Life',value: `${v.oil_life}%`, alert: v.oil_life < 15 },
          ];
        } else {
          // backend returned {detail:"Not found"}
          this.vehicle = null;
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.vehicle = null;
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
}

  private loadWarranty() {
    this.api.checkWarranty(this.vehicleCode, this.repairType)
      .subscribe(r => this.ngZone.run(() => {
        this.result = r;
        this.cdr.markForCheck();
      }));
  }
}