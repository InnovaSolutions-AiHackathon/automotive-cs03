import { ChangeDetectorRef, Component, Input, NgZone, OnInit } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-vehicle-dashboard',
  standalone: true,
  imports: [CommonModule, DecimalPipe],
  templateUrl: './vehicle-dashboard.component.html',
  styleUrls: ['./vehicle-dashboard.component.scss']

})
export class VehicleDashboardComponent implements OnInit {
  @Input() vehicleCode = 'VH001';

  @Input() vehicleId = 'VH001';
  @Input() repairType = 'engine';

  result: any = null;
  vehicle: any = null;
  loading = true;

  stats: { icon: string; label: string; value: string; alert: boolean }[] = [];

  constructor(private api: ApiService, private ngZone: NgZone, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    
    this.api.getVehicle(this.vehicleCode).subscribe({
      next: (v) => {
        this.vehicle = v;
        this.loading = false;
        this.stats = [
          { icon: '⛽', label: 'Fuel',    value: `${v.fuel_level}%`,        alert: v.fuel_level < 20 },
          { icon: '🔋', label: 'Battery', value: `${v.battery_voltage}V`,   alert: v.battery_voltage < 12.0 },
          { icon: '🌡️', label: 'Engine',  value: `${v.engine_temp}°C`,     alert: v.engine_temp > 105 },
          { icon: '🛢️', label: 'Oil Life',value: `${v.oil_life}%`,         alert: v.oil_life < 15 },
        ];
        
        this.cdr.markForCheck();

      },
      error: () => { this.loading = false; }
    });
      
  this.api.checkWarranty(this.vehicleId, this.repairType)
    .subscribe(r => this.ngZone.run(() => { this.result = r; this.cdr.markForCheck(); }));

  }
}