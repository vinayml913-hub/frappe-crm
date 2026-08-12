import frappe


@frappe.whitelist()
def get_deal_commercial_calculator_script():
	return """// CRM Deal Commercial Calculator
//
// Mirrors crm_deal.py's calculate_financials() EXACTLY, so the Proposed/
// Landing totals, GST-adjusted display totals, and Gross Profit update
// live in the browser as the user types - in both the Create Deal
// (Quick Entry) modal and the full Deal form/sidebar, since both use the
// same generic FieldLayout -> triggerOnChange() -> this[fieldname]()
// mechanism this script hooks into.
//
// Costing Type, No. of Days/Hours, Lab Pax, and Certification/Voucher Pax
// are entered ONCE (in the Proposed section) and shared by both Proposed
// and Landing - the delivery format/duration/headcount don't change
// between what was quoted and what actually happened, only the RATES do.
//
// The Python calculate_financials() on the server remains the source of
// truth and runs again on save/validate - this script only gives instant
// visual feedback before that save happens. If you ever change the
// formula, change it in BOTH places.

function round2(value) {
	return Math.round((Number(value) || 0) * 100) / 100
}

// Trainer Cost = Commercial x Days (or Hours), using the shared Costing
// Type/No. of Days/No. of Hours fields.
function trainerLeg(commercial, d) {
	commercial = Number(commercial) || 0
	if (d.trainer_costing_type === 'Per Day') return commercial * (Number(d.trainer_no_of_days) || 0)
	if (d.trainer_costing_type === 'Per Hour') return commercial * (Number(d.trainer_no_of_hours) || 0)
	return commercial
}

// Lab Total = Cost x Lab Pax x Days/Hours, using the shared Lab Costing
// Type/No. of Days/No. of Hours/Lab Pax fields. "Total Lab Costing" is a
// flat rate-per-participant - Cost x Pax, no days/hours multiplier.
// Pax defaults to 1 if left blank, so an empty headcount never silently
// zeroes out the whole leg.
function labLeg(cost, d) {
	cost = Number(cost) || 0
	const pax = Number(d.lab_pax) || 1
	if (d.lab_costing_type === 'Per Day') return cost * pax * (Number(d.lab_no_of_days) || 0)
	if (d.lab_costing_type === 'Per Hour') return cost * pax * (Number(d.lab_no_of_hours) || 0)
	// "Total Lab Costing" (or blank) - flat rate-per-participant.
	return cost * pax
}

// Certification Total = Certification/Voucher Costing x Certification Pax
// (its own headcount, independent of Lab Pax). Pax defaults to 1 if
// blank, same reasoning as Lab Pax above.
function certificationLeg(cost, d) {
	const pax = Number(d.certification_pax) || 1
	return (Number(cost) || 0) * pax
}

class CRMDeal {
	// Run once when the form loads/re-renders, so totals are already
	// correct when opening an existing Deal for editing - not just after
	// the next field change.
	refresh() {
		this.calculate()
	}

	// Shared inputs (Costing Type/Days/Hours/Pax) - used by BOTH Proposed
	// and Landing, entered once.
	trainer_costing_type() { this.calculate() }
	trainer_no_of_days() { this.calculate() }
	trainer_no_of_hours() { this.calculate() }
	lab_costing_type() { this.calculate() }
	lab_no_of_days() { this.calculate() }
	lab_no_of_hours() { this.calculate() }
	lab_pax() { this.calculate() }
	certification_pax() { this.calculate() }

	// Proposed Cost (Quoted) rate inputs
	proposed_trainer_commercial() { this.calculate() }
	proposed_lab_cost() { this.calculate() }
	proposed_certification_cost() { this.calculate() }
	proposed_misc_expense() { this.calculate() }
	// Flipping the override off snaps straight back to the auto value.
	proposed_total_override() { this.calculate() }

	// Landing Cost (Expenses) rate inputs
	landing_trainer_commercial() { this.calculate() }
	landing_lab_cost() { this.calculate() }
	landing_certification_cost() { this.calculate() }
	landing_misc_expense() { this.calculate() }
	landing_total_override() { this.calculate() }

	// GST (display-only toggle - never affects Gross Profit)
	gst_type() { this.calculate() }
	gst_percentage() { this.calculate() }

	calculate() {
		const d = this.doc

		const proposedTrainerCost = trainerLeg(d.proposed_trainer_commercial, d)
		const proposedLabTotal = labLeg(d.proposed_lab_cost, d)
		const proposedCertificationTotal = certificationLeg(d.proposed_certification_cost, d)
		// Proposed Total: auto-calculated UNLESS the manual override is
		// checked, in which case whatever the user typed is left alone.
		const proposedTotal = d.proposed_total_override
			? Number(d.proposed_total) || 0
			: proposedTrainerCost +
				proposedLabTotal +
				proposedCertificationTotal +
				(Number(d.proposed_misc_expense) || 0)

		const landingTrainerCost = trainerLeg(d.landing_trainer_commercial, d)
		const landingLabTotal = labLeg(d.landing_lab_cost, d)
		const landingCertificationTotal = certificationLeg(d.landing_certification_cost, d)
		// Landing Total: same manual-override rule as Proposed Total above.
		const landingTotal = d.landing_total_override
			? Number(d.landing_total) || 0
			: landingTrainerCost +
				landingLabTotal +
				landingCertificationTotal +
				(Number(d.landing_misc_expense) || 0)

		// GST only affects the DISPLAYED totals, never Gross Profit.
		const gstPct = Number(d.gst_percentage) || 18
		let proposedTotalWithGst = proposedTotal
		let landingTotalWithGst = landingTotal
		if (d.gst_type === 'Including GST') {
			proposedTotalWithGst = proposedTotal * (1 + gstPct / 100)
			landingTotalWithGst = landingTotal * (1 + gstPct / 100)
		}

		// Gross Profit - always pre-GST, feeds the dashboard/target.
		const grossProfit = proposedTotal - landingTotal
		const grossProfitPct = proposedTotal ? (grossProfit / proposedTotal) * 100 : 0

		this.doc.proposed_trainer_cost = round2(proposedTrainerCost)
		this.doc.proposed_lab_total = round2(proposedLabTotal)
		this.doc.proposed_certification_total = round2(proposedCertificationTotal)
		this.doc.proposed_total = round2(proposedTotal)

		this.doc.landing_trainer_cost = round2(landingTrainerCost)
		this.doc.landing_lab_total = round2(landingLabTotal)
		this.doc.landing_certification_total = round2(landingCertificationTotal)
		this.doc.landing_total = round2(landingTotal)

		this.doc.proposed_total_with_gst = round2(proposedTotalWithGst)
		this.doc.landing_total_with_gst = round2(landingTotalWithGst)

		this.doc.gross_profit = round2(grossProfit)
		this.doc.gross_profit_pct = round2(grossProfitPct)
	}
}
"""
